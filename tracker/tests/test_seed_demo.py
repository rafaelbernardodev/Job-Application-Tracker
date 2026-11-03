from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone

from tracker.models import Application


def test_seed_demo_creates_requested_number_of_applications(db):
    call_command("seed_demo", count=20)

    demo = get_user_model().objects.get(username="demo")
    assert Application.objects.filter(user=demo).count() == 20


def test_seed_demo_is_safe_to_rerun(db):
    call_command("seed_demo", count=10)
    call_command("seed_demo", count=10)

    assert Application.objects.count() == 10


def test_seeded_histories_are_consistent(db):
    call_command("seed_demo", count=40)
    now = timezone.now()

    for application in Application.objects.all():
        last_event = application.events.last()
        assert last_event.status == application.current_status
        assert last_event.occurred_at <= now