import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from tracker.models import Application


def test_unauthenticated_requests_are_rejected(db):
    response = APIClient().get(reverse("application-list"))
    # Session auth has no WWW-Authenticate header, so DRF returns 403, not 401
    assert response.status_code == 403


def test_list_only_returns_own_applications(auth_client, application, other_application):
    response = auth_client.get(reverse("application-list"))

    assert response.status_code == 200
    ids = [item["id"] for item in response.data]
    assert ids == [application.id]


def test_cannot_retrieve_another_users_application(auth_client, other_application):
    url = reverse("application-detail", args=[other_application.id])
    assert auth_client.get(url).status_code == 404


def test_cannot_modify_or_delete_another_users_application(auth_client, other_application):
    url = reverse("application-detail", args=[other_application.id])
    assert auth_client.patch(url, {"job_title": "Hacked"}, format="json").status_code == 404
    assert auth_client.delete(url).status_code == 404


def test_create_application_sets_owner_and_initial_event(auth_client, user, company):
    response = auth_client.post(
        reverse("application-list"),
        {"company": company.id, "job_title": "Backend Developer"},
        format="json",
    )

    assert response.status_code == 201
    created = Application.objects.get(pk=response.data["id"])
    assert created.user == user
    assert created.events.count() == 1


def test_cannot_create_application_with_another_users_company(
    auth_client, other_application
):
    response = auth_client.post(
        reverse("application-list"),
        {"company": other_application.company.id, "job_title": "Sneaky"},
        format="json",
    )
    assert response.status_code == 400


def test_current_status_cannot_be_set_directly(auth_client, application):
    url = reverse("application-detail", args=[application.id])
    auth_client.patch(url, {"current_status": "offer"}, format="json")

    application.refresh_from_db()
    assert application.current_status == Application.Status.APPLIED


def test_change_status_endpoint(auth_client, application):
    url = reverse("application-change-status", args=[application.id])
    response = auth_client.post(
        url, {"status": "interview", "notes": "Phone screen"}, format="json"
    )

    assert response.status_code == 200
    assert response.data["current_status"] == "interview"
    assert len(response.data["events"]) == 2


def test_change_status_rejects_invalid_status(auth_client, application):
    url = reverse("application-change-status", args=[application.id])
    response = auth_client.post(url, {"status": "banana"}, format="json")
    assert response.status_code == 400


def test_cannot_change_status_of_another_users_application(auth_client, other_application):
    url = reverse("application-change-status", args=[other_application.id])
    response = auth_client.post(url, {"status": "offer"}, format="json")
    assert response.status_code == 404


def test_duplicate_company_name_returns_400(auth_client, company):
    response = auth_client.post(
        reverse("company-list"), {"name": company.name.upper()}, format="json"
    )
    assert response.status_code == 400