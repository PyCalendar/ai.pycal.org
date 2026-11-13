"""People sign in with an OAuth app without scopes; the app reads their roles by itself."""

import os

import pytest

from ai_pycal import registered_settings

pytestmark = pytest.mark.django_db
NAMES = ("GITHUB_OAUTH_CLIENT_ID", "GITHUB_OAUTH_SECRET")


@pytest.fixture
def site(settings, tmp_path, monkeypatch):
    settings.DATA_DIR = tmp_path
    settings.SIGN_IN_WITH_OAUTH_APP = False
    for name in NAMES:
        monkeypatch.delenv(name, raising=False)
    yield settings
    for name in NAMES:
        os.environ.pop(name, None)


def test_setup_says_that_nobody_can_sign_in_without_it(client, site, maintainer, repository):
    client.force_login(maintainer)  # a session from before: signing in is not possible
    page = client.get("/setup/").content.decode()
    assert "data-oauth-missing" in page and 'href="/setup/oauth-app/"' in page
    assert "Nobody can sign in until the OAuth app is entered." in page


def test_the_sign_in_page_leads_to_the_setup_of_signing_in(client, site):
    page = client.get("/accounts/login/").content.decode()
    assert "data-no-sign-in" in page and 'href="/setup/oauth-app/"' in page
    assert 'action="/accounts/github/login/' not in page


def test_the_people_who_run_the_site_enter_it_with_the_setup_code(client, site, tmp_path):
    from ai_pycal.services.app_registration import AppRegistration

    site.DEBUG = False
    page = client.get("/setup/oauth-app/").content.decode()  # nobody can sign in yet
    assert 'name="setup_code"' in page and "data-oauth-missing" in page
    values = {"client_id": "Ov23liOAUTHclient", "secret": "s" * 40}
    response = client.post("/setup/oauth-app/", {**values, "setup_code": "wrong"})
    assert (
        response.status_code == 403 and 'data-error="SetupCodeWrong"' in response.content.decode()
    )
    assert not (tmp_path / ".env").exists()
    response = client.post(
        "/setup/oauth-app/", {**values, "setup_code": AppRegistration.setup_code()}
    )
    assert response.status_code == 302 and response["Location"] == "/accounts/login/"
    assert site.SIGN_IN_WITH_OAUTH_APP
    assert 'action="/accounts/github/login/' in client.get("/accounts/login/").content.decode()


def test_once_it_is_set_only_site_admins_change_it(client, site, alice, maintainer):
    site.SIGN_IN_WITH_OAUTH_APP = True
    response = client.get("/setup/oauth-app/")
    assert response.status_code == 302 and "/accounts/login/" in response["Location"]
    client.force_login(alice)
    assert client.get("/setup/oauth-app/").status_code == 403
    assert (
        client.post("/setup/oauth-app/", {"client_id": "a" * 10, "secret": "s" * 40}).status_code
        == 403
    )
    site.SITE_ADMINS = ["maintainer"]
    client.force_login(maintainer)
    page = client.get("/setup/oauth-app/").content.decode()
    assert 'name="client_id"' in page and 'name="setup_code"' not in page


def test_the_oauth_app_is_kept_in_the_volume(client, site, maintainer, tmp_path):
    site.SITE_ADMINS = ["maintainer"]
    client.force_login(maintainer)
    page = client.get("/setup/oauth-app/").content.decode()
    assert "https://ai.example.org/accounts/github/login/callback/" in page
    response = client.post(
        "/setup/oauth-app/", {"client_id": "Ov23liOAUTHclient", "secret": "s" * 40}
    )
    assert response.status_code == 302
    saved = registered_settings.read(tmp_path / ".env")
    assert saved == {"GITHUB_OAUTH_CLIENT_ID": "Ov23liOAUTHclient", "GITHUB_OAUTH_SECRET": "s" * 40}
    assert site.SIGN_IN_WITH_OAUTH_APP
    assert site.SOCIALACCOUNT_PROVIDERS["github"]["APP"]["client_id"] == "Ov23liOAUTHclient"
    assert "data-oauth-missing" not in client.get("/setup/").content.decode()


def test_wrong_values_are_refused(client, site, maintainer, tmp_path):
    site.SITE_ADMINS = ["maintainer"]
    client.force_login(maintainer)
    response = client.post("/setup/oauth-app/", {"client_id": "x", "secret": "short"})
    assert response.status_code == 400
    assert not (tmp_path / ".env").exists()


def test_the_environment_takes_precedence(client, site, maintainer, monkeypatch, tmp_path):
    monkeypatch.setenv("GITHUB_OAUTH_CLIENT_ID", "from-the-environment")
    site.SITE_ADMINS = ["maintainer"]
    client.force_login(maintainer)
    page = client.get("/setup/oauth-app/").content.decode()
    assert "set in the environment" in page and 'name="client_id"' not in page
    client.post("/setup/oauth-app/", {"client_id": "a" * 10, "secret": "s" * 40})
    assert not (tmp_path / ".env").exists()


def test_signing_in_asks_only_for_the_email_addresses():
    from ai_pycal import settings as site_settings

    assert site_settings.SOCIALACCOUNT_PROVIDERS["github"]["SCOPE"] == ["user:email"]
    assert site_settings.SOCIALACCOUNT_QUERY_EMAIL is True
    assert site_settings.SOCIALACCOUNT_STORE_TOKENS is False


def test_the_settings_choose_the_oauth_app(monkeypatch, tmp_path):
    import subprocess
    import sys
    from pathlib import Path

    environment = dict(
        os.environ,
        DEBUG="1",
        DATA_DIR=str(tmp_path),
        GITHUB_CLIENT_ID="app-client",
        GITHUB_SECRET="app-secret",
        GITHUB_OAUTH_CLIENT_ID="oauth-client",
        GITHUB_OAUTH_SECRET="oauth-secret",
        DJANGO_SETTINGS_MODULE="ai_pycal.settings",
    )
    code = (
        "from django.conf import settings; "
        "print(settings.SOCIALACCOUNT_PROVIDERS['github']['APP']['client_id'])"
    )

    def client_id(environment):
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=Path(__file__).parents[2],
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    assert client_id(environment) == "oauth-client"
    # the GitHub App never signs people in: without the OAuth app, nobody can
    environment["GITHUB_OAUTH_CLIENT_ID"] = ""
    code = "from django.conf import settings; print(settings.SOCIALACCOUNT_PROVIDERS['github'])"
    assert "app-client" not in client_id(environment)


def test_the_verified_addresses_of_github_are_kept(alice, bob):
    from allauth.account.models import EmailAddress

    from ai_pycal.signals import keep_verified_addresses

    account = alice.socialaccount_set.get()
    account.extra_data["emails"] = [
        {"email": "alice@example.org", "primary": True, "verified": True},
        {"email": "unverified@example.org", "primary": False, "verified": False},
        {"email": "shared@example.org", "primary": False, "verified": True},
    ]
    account.save()
    EmailAddress.objects.create(user=bob, email="shared@example.org", verified=True)
    assert keep_verified_addresses(alice) == 1
    found = EmailAddress.objects.get(user=alice)
    assert found.email == "alice@example.org" and found.verified and found.primary
    assert keep_verified_addresses(alice) == 0  # nothing new at the next sign-in


def test_signing_in_keeps_the_addresses(rf, alice):
    from allauth.account.models import EmailAddress
    from allauth.account.signals import user_logged_in

    account = alice.socialaccount_set.get()
    account.extra_data["emails"] = [{"email": "a@example.org", "primary": True, "verified": True}]
    account.save()
    user_logged_in.send(sender=None, request=rf.get("/"), user=alice)
    assert EmailAddress.objects.get(user=alice).verified
