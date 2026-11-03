import pandas as pd
import pytest
from django.core.management import call_command
from django.urls import reverse
from django.contrib.auth import get_user_model

from tracker.analytics import ApplicationAnalytics


@pytest.fixture
def analytics():
    """Four hand-made applications, so every expected number below is checkable by eye."""
    applications = pd.DataFrame([
        {"id": 1, "source": "referral", "date_applied": "2026-01-05"},
        {"id": 2, "source": "linkedin", "date_applied": "2026-01-06"},
        {"id": 3, "source": "linkedin", "date_applied": "2026-01-12"},
        {"id": 4, "source": "linkedin", "date_applied": "2026-01-27"},
    ])
    events = pd.DataFrame([
        # 1: full success path
        {"application_id": 1, "status": "applied", "occurred_at": "2026-01-05"},
        {"application_id": 1, "status": "screening", "occurred_at": "2026-01-08"},
        {"application_id": 1, "status": "interview", "occurred_at": "2026-01-15"},
        {"application_id": 1, "status": "offer", "occurred_at": "2026-01-25"},
        # 2: screening, then rejected
        {"application_id": 2, "status": "applied", "occurred_at": "2026-01-06"},
        {"application_id": 2, "status": "screening", "occurred_at": "2026-01-16"},
        {"application_id": 2, "status": "rejected", "occurred_at": "2026-01-20"},
        # 3: instant auto-rejection (not a "response")
        {"application_id": 3, "status": "applied", "occurred_at": "2026-01-12"},
        {"application_id": 3, "status": "rejected", "occurred_at": "2026-01-20"},
        # 4: still waiting
        {"application_id": 4, "status": "applied", "occurred_at": "2026-01-27"},
    ])
    return ApplicationAnalytics(applications, events)


def test_funnel_counts_and_conversion(analytics):
    funnel = analytics.funnel().set_index("stage")

    assert funnel["count"].to_dict() == {
        "applied": 4, "screening": 2, "interview": 1, "offer": 1,
    }
    assert funnel.loc["screening", "from_previous"] == pytest.approx(0.5)
    assert funnel.loc["interview", "from_previous"] == pytest.approx(0.5)
    assert funnel.loc["offer", "from_applied"] == pytest.approx(0.25)


def test_response_rate_by_source(analytics):
    result = analytics.response_rate_by_source().set_index("source")

    assert result.loc["referral", "response_rate"] == pytest.approx(1.0)
    # 1 of 3 LinkedIn applications reached screening; the auto-rejection doesn't count
    assert result.loc["linkedin", "applications"] == 3
    assert result.loc["linkedin", "responses"] == 1
    assert result.loc["linkedin", "response_rate"] == pytest.approx(0.333, abs=0.001)


def test_time_to_stage(analytics):
    result = analytics.time_to_stage().set_index("stage")

    # Screening took 3 days for application 1 and 10 days for application 2
    assert result.loc["screening", "count"] == 2
    assert result.loc["screening", "mean_days"] == pytest.approx(6.5)
    assert result.loc["offer", "mean_days"] == pytest.approx(20.0)


def test_weekly_volume_includes_empty_weeks(analytics):
    result = analytics.weekly_volume()

    assert result["applications"].tolist() == [2, 1, 0, 1]


def test_empty_data_does_not_crash(user):
    analytics = ApplicationAnalytics.from_user(user)

    assert analytics.funnel()["count"].tolist() == [0, 0, 0, 0]
    assert analytics.response_rate_by_source().empty
    assert analytics.time_to_stage().empty
    assert analytics.weekly_volume().empty


def test_from_user_only_includes_that_users_data(user, application, other_application):
    analytics = ApplicationAnalytics.from_user(user)

    assert analytics.applications["id"].tolist() == [application.id]


def test_seeded_funnel_never_increases(db):
    call_command("seed_demo", count=40)
    demo = get_user_model().objects.get(username="demo")

    funnel = ApplicationAnalytics.from_user(demo).funnel()

    assert funnel.loc[0, "count"] == 40
    assert funnel["count"].is_monotonic_decreasing


def test_analytics_endpoint(auth_client, application):
    response = auth_client.get(reverse("analytics"))

    assert response.status_code == 200
    assert set(response.data) == {
        "funnel", "response_rate_by_source", "time_to_stage", "weekly_volume",
    }
    assert response.data["funnel"][0]["count"] == 1