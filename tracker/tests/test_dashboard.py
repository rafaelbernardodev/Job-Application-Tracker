from django.urls import reverse


def test_dashboard_redirects_anonymous_users_to_login(client):
    response = client.get(reverse("dashboard"))

    assert response.status_code == 302
    assert "login" in response.url


def test_dashboard_renders_for_logged_in_user(client, user):
    client.force_login(user)

    response = client.get(reverse("dashboard"))

    assert response.status_code == 200
    assert b'id="funnel"' in response.content