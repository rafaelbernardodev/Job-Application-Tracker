import pytest
from django.contrib.auth import get_user_model

from tracker.models import Application, Company


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