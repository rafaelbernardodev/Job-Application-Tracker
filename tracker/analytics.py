import pandas as pd

from .models import Application, StatusEvent

FUNNEL_STAGES = ["applied", "screening", "interview", "offer"]

# "Response" means a company engaged with you: you reached screening or later.
# An instant auto-rejection is not counted as a response.
RESPONSE_STATUSES = ["screening", "interview", "offer"]

APPLICATION_FIELDS = [
    "id", "source", "job_title", "work_mode",
    "date_applied", "current_status", "company__name",
]
EVENT_FIELDS = ["application_id", "status", "occurred_at"]


def _ratio(numerator, denominator):
    if not denominator:  # None or 0
        return None
    return round(numerator / denominator, 3)


def to_records(df):
    """DataFrame -> list of dicts that are safe to send as JSON (NaN becomes None)."""
    return df.astype(object).where(df.notna(), None).to_dict("records")


class ApplicationAnalytics:
    def __init__(self, applications, events):
        self.applications = applications.copy()
        self.events = events.copy()
        self.applications["date_applied"] = pd.to_datetime(self.applications["date_applied"])
        self.events["occurred_at"] = pd.to_datetime(self.events["occurred_at"], utc=True)

    @classmethod
    def from_user(cls, user):
        """Build the DataFrames once, with two queries, from one user's data."""
        applications = pd.DataFrame(
            list(Application.objects.filter(user=user).values(*APPLICATION_FIELDS)),
            columns=APPLICATION_FIELDS,
        )
        events = pd.DataFrame(
            list(StatusEvent.objects.filter(application__user=user).values(*EVENT_FIELDS)),
            columns=EVENT_FIELDS,
        )
        return cls(applications, events)

    def funnel(self):
        """How many applications reached each stage, and the conversion rates."""
        reached = self.events.groupby("status")["application_id"].nunique()

        rows, previous, first = [], None, None
        for stage in FUNNEL_STAGES:
            count = int(reached.get(stage, 0))
            if first is None:
                first = count
            rows.append({
                "stage": stage,
                "count": count,
                "from_previous": _ratio(count, previous),
                "from_applied": _ratio(count, first),
            })
            previous = count
        return pd.DataFrame(rows)

    def response_rate_by_source(self):
        """Share of applications per source that got a real response."""
        columns = ["source", "applications", "responses", "response_rate"]
        if self.applications.empty:
            return pd.DataFrame(columns=columns)

        responded_ids = self.events.loc[
            self.events["status"].isin(RESPONSE_STATUSES), "application_id"
        ].unique()
        df = self.applications.assign(responded=self.applications["id"].isin(responded_ids))

        result = df.groupby("source")["responded"].agg(applications="count", responses="sum")
        result["response_rate"] = (result["responses"] / result["applications"]).round(3)
        return result.sort_values("response_rate", ascending=False).reset_index()

    def time_to_stage(self):
        """Days from 'applied' to the first time each stage was reached."""
        columns = ["stage", "count", "mean_days", "median_days"]
        if self.events.empty:
            return pd.DataFrame(columns=columns)

        # One row per application, one column per status, holding the first timestamp
        first = (
            self.events.groupby(["application_id", "status"])["occurred_at"]
            .min()
            .unstack("status")
        )
        if "applied" not in first:
            return pd.DataFrame(columns=columns)

        rows = []
        for stage in ["screening", "interview", "offer", "rejected"]:
            if stage not in first:
                continue
            days = (first[stage] - first["applied"]).dt.total_seconds().div(86400).dropna()
            if days.empty:
                continue
            rows.append({
                "stage": stage,
                "count": len(days),
                "mean_days": round(days.mean(), 1),
                "median_days": round(days.median(), 1),
            })
        return pd.DataFrame(rows, columns=columns)

    def weekly_volume(self):
        """Applications sent per week (weeks end on Sunday), including empty weeks."""
        columns = ["week_ending", "applications"]
        if self.applications.empty:
            return pd.DataFrame(columns=columns)

        weekly = (
            self.applications.set_index("date_applied")["id"]
            .resample("W")
            .count()
            .rename("applications")
            .reset_index()
            .rename(columns={"date_applied": "week_ending"})
        )
        weekly["week_ending"] = weekly["week_ending"].dt.date
        return weekly