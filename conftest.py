import pytest
from django.contrib.auth import get_user_model

from tracker.models import Application, Company

from rest_framework.test import APIClient


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(username="rafael", password="pass1234")


@pytest.fixture
def company(user):
    return Company.objects.create(user=user, name="Acme")


@pytest.fixture
def application(user, company):
    return Application.objects.create(
        user=user, company=company, job_title="Junior Python Developer"
    )

@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def other_user(db):
    return get_user_model().objects.create_user(username="intruder", password="pass1234")


@pytest.fixture
def other_application(other_user):
    other_company = Company.objects.create(user=other_user, name="Secret Corp")
    return Application.objects.create(
        user=other_user, company=other_company, job_title="Someone else's job"
    )