"""The pages of the site and signing in with GitHub only."""

import pytest
from django.contrib.auth import get_user_model

from tests.conftest import person

pytestmark = pytest.mark.django_db


def test_the_start_page(client):
    page = client.get("/").content.decode()
    assert "Agreements for pull requests" in page
    assert "Sign in with GitHub" in page
    assert "https://docs.ai.pycal.org/" in page


def test_sign_in_without_client_explains_the_setup(client, settings):
    """Without GITHUB_CLIENT_ID, as in a new development setup, the error is explained."""
    settings.SOCIALACCOUNT_PROVIDERS = {"github": {"SCOPE": []}}
    response = client.get("/accounts/login/")
    page = response.content.decode()
    assert response.status_code == 503
    assert "Signing in with GitHub is not configured" in page
    assert "GITHUB_CLIENT_ID" in page
    assert "errors.html#ai_pycal.errors.github.SignInNotConfigured" in page


def test_health(client):
    assert client.get("/health/").json() == {"status": "ok"}


def test_sign_in_is_with_github_only(client):
    page = client.get("/accounts/login/").content.decode()
    assert 'action="/accounts/github/login/' in page
    assert 'type="password"' not in page
    assert (
        client.get("/accounts/signup/").status_code in (302, 404)
        or b"password" not in client.get("/accounts/signup/").content
    )


def test_site_admins_administer(settings):
    from allauth.account.signals import user_logged_in

    settings.SITE_ADMINS = ["maintainer"]
    admin = person(1, "Maintainer")
    other = person(2, "other")
    for user in (admin, other):
        user_logged_in.send(sender=get_user_model(), request=None, user=user)
        user.refresh_from_db()
    assert admin.is_staff and admin.is_superuser
    assert not other.is_staff


def test_pages_can_not_be_framed(client):
    assert client.get("/").headers["X-Frame-Options"] == "DENY"


@pytest.mark.parametrize("url", ["http://localhost:8000/", "https://docs.example/preview"])
def test_documentation_navigation_and_error_help_share_the_configured_url(client, settings, url):
    settings.DOCS_URL = url
    base = url.rstrip("/") + "/"
    page = client.get("/").content.decode()
    assert f'href="{base}"' in page
    assert f'href="{base}changelog.html"' in page
    settings.SOCIALACCOUNT_PROVIDERS = {"github": {"SCOPE": []}}
    response = client.get("/accounts/login/")
    assert response.status_code == 503
    page = response.content.decode()
    assert f"{base}reference/errors.html#ai_pycal.errors.github.SignInNotConfigured" in page
    assert f"{base}how-to/github-app.html" in page
