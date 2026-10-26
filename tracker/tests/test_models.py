import pytest
from django.db import IntegrityError

from tracker.models import Application, Company


def test_new_application_gets_initial_applied_event(application):
    events = list(application.events.all())

    assert len(events) == 1
    assert events[0].status == Application.Status.APPLIED
    assert application.current_status == Application.Status.APPLIED


def test_change_status_creates_event_and_updates_current_status(application):
    application.change_status(Application.Status.INTERVIEW, notes="Phone screen")

    application.refresh_from_db()
    assert application.current_status == Application.Status.INTERVIEW
    assert application.events.count() == 2
    assert application.events.last().notes == "Phone screen"


def test_saving_existing_application_does_not_create_new_event(application):
    application.job_title = "Backend Developer"
    application.save()

    assert application.events.count() == 1


def test_company_names_are_unique_per_user_ignoring_case(user, company):
    with pytest.raises(IntegrityError):
        Company.objects.create(user=user, name="acme")