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


def test_site_admins_are_told_to_set_up_the_oauth_app(client, site, maintainer, repository):
    client.force_login(maintainer)
    assert "data-oauth-missing" not in client.get("/setup/").content.decode()
    site.SITE_ADMINS = ["maintainer"]
    page = client.get("/setup/").content.decode()
    assert "data-oauth-missing" in page and 'href="/setup/oauth-app/"' in page


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


def test_only_site_admins_enter_it(client, site, alice):
    client.force_login(alice)
    assert client.get("/setup/oauth-app/").status_code == 403
    assert (
        client.post("/setup/oauth-app/", {"client_id": "a" * 10, "secret": "s" * 40}).status_code
        == 403
    )


def test_the_environment_takes_precedence(client, site, maintainer, monkeypatch, tmp_path):
    monkeypatch.setenv("GITHUB_OAUTH_CLIENT_ID", "from-the-environment")
    site.SITE_ADMINS = ["maintainer"]
    client.force_login(maintainer)
    page = client.get("/setup/oauth-app/").content.decode()
    assert "set in the environment" in page and 'name="client_id"' not in page
    client.post("/setup/oauth-app/", {"client_id": "a" * 10, "secret": "s" * 40})
    assert not (tmp_path / ".env").exists()


def test_signing_in_asks_no_scope(settings):
    assert settings.SOCIALACCOUNT_PROVIDERS["github"]["SCOPE"] == []
    assert settings.SOCIALACCOUNT_STORE_TOKENS is False


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
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).parents[2],
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "oauth-client"
