"""The site registers its own GitHub App and keeps the credentials in its volume."""

import json
import os
import signal
from html import unescape

import pytest

from ai_pycal import registered_settings
from ai_pycal.services import app_registration
from ai_pycal.services.app_registration import SESSION_KEY, AppRegistration

pytestmark = pytest.mark.django_db

NEW_APP = {
    "id": 4242,
    "slug": "ai-pycal-new",
    "name": "ai-pycal-new",
    "client_id": "Iv1.new",
    "client_secret": "client-secret",
    "webhook_secret": "hook-secret",
    "pem": "-----BEGIN RSA PRIVATE KEY-----\\nkey\\n-----END RSA PRIVATE KEY-----\\n",
    "html_url": "https://github.com/apps/ai-pycal-new",
    "owner": {"login": "PyCalendar"},
}
GITHUB_NAMES = app_registration.ENVIRONMENT_NAMES + ("GITHUB_APP_PRIVATE_KEY_FILE",)


@pytest.fixture
def new_site(settings, tmp_path, monkeypatch):
    """A site without a GitHub App, with its volume in a temporary directory."""
    settings.DATA_DIR = tmp_path
    settings.DEBUG = False
    settings.GITHUB_APP_ID = ""
    settings.GITHUB_APP_SLUG = ""
    settings.GITHUB_APP_PRIVATE_KEY = ""
    settings.GITHUB_WEBHOOK_SECRET = ""
    settings.SOCIALACCOUNT_PROVIDERS = {"github": {"SCOPE": []}}
    for name in GITHUB_NAMES:
        monkeypatch.delenv(name, raising=False)
    yield settings
    for name in GITHUB_NAMES:  # apply() writes into os.environ
        os.environ.pop(name, None)


def start(client, **fields):
    data = {"name": "ai-pycal-new", "organization": "", "setup_code": AppRegistration.setup_code()}
    data.update(fields)
    return client.post("/setup/github-app/", data)


def test_the_page_offers_the_registration(client, new_site):
    page = client.get("/setup/github-app/").content.decode()
    assert 'name="setup_code"' in page
    assert "Register GitHub App" in page
    assert "data-local" not in page  # https://ai.example.org is public


def test_registration_sends_the_manifest_to_github(client, new_site):
    response = start(client, organization="PyCalendar")
    assert response.status_code == 200
    page = response.content.decode()
    state = client.session[SESSION_KEY]
    assert (
        f'action="https://github.com/organizations/PyCalendar/settings/apps/new?state={state}"'
        in page
    )
    manifest = json.loads(unescape(page.split('name="manifest" value="')[1].split('"')[0]))
    assert manifest["name"] == "ai-pycal-new"
    assert manifest["redirect_url"] == "https://ai.example.org/setup/github-app/registered/"
    assert manifest["hook_attributes"]["url"] == "https://ai.example.org/github/webhook/"
    assert "Continue to GitHub" in page


def test_github_returns_and_the_credentials_are_saved(client, new_site, github, tmp_path):
    start(client)
    state = client.session[SESSION_KEY]
    github.manifest_codes["the-code"] = dict(NEW_APP)
    response = client.get(f"/setup/github-app/registered/?code=the-code&state={state}")
    assert response.status_code == 200
    page = response.content.decode()
    assert 'data-registered-app="ai-pycal-new"' in page
    assert "https://github.com/apps/ai-pycal-new/installations/new" in page
    saved = registered_settings.read(tmp_path / ".env")
    assert saved == {
        "GITHUB_APP_ID": "4242",
        "GITHUB_APP_SLUG": "ai-pycal-new",
        "GITHUB_CLIENT_ID": "Iv1.new",
        "GITHUB_SECRET": "client-secret",
        "GITHUB_WEBHOOK_SECRET": "hook-secret",
        "GITHUB_APP_PRIVATE_KEY_FILE": str(tmp_path / "github-app.pem"),
    }
    assert (tmp_path / "github-app.pem").read_text() == NEW_APP["pem"]
    assert oct((tmp_path / ".env").stat().st_mode & 0o777) == "0o600"
    assert oct((tmp_path / "github-app.pem").stat().st_mode & 0o777) == "0o600"
    assert not (tmp_path / "github-app-setup-code").exists()
    # the site uses the app at once, and registers no other
    assert new_site.GITHUB_APP_ID == "4242"
    assert new_site.SOCIALACCOUNT_PROVIDERS["github"]["APP"]["client_id"] == "Iv1.new"
    assert AppRegistration.source() == "volume"
    again = start(client)
    assert again.status_code == 409
    assert 'data-registered="volume"' in again.content.decode()
    assert 'data-registered="volume"' in client.get("/setup/github-app/").content.decode()
    assert 'action="/accounts/github/login/' in client.get("/accounts/login/").content.decode()


def test_the_registered_settings_are_read_at_start_with_the_environment_first(tmp_path):
    registered_settings.write(tmp_path / ".env", {"GITHUB_APP_ID": "4242", "GITHUB_SECRET": "s"})
    environ = {"GITHUB_APP_ID": "7", "GITHUB_SECRET": ""}
    assert registered_settings.load(tmp_path / ".env", environ) == ["GITHUB_SECRET"]
    assert environ == {"GITHUB_APP_ID": "7", "GITHUB_SECRET": "s"}


def test_the_key_goes_to_the_configured_file(client, new_site, github, tmp_path, monkeypatch):
    key = tmp_path / "keys" / "app.pem"
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_FILE", str(key))
    start(client)
    github.manifest_codes["c"] = dict(NEW_APP)
    client.get(f"/setup/github-app/registered/?code=c&state={client.session[SESSION_KEY]}")
    assert key.read_text() == NEW_APP["pem"]
    assert not (tmp_path / "github-app.pem").exists()


def test_an_existing_key_is_never_overwritten(client, new_site, tmp_path):
    (tmp_path / "github-app.pem").write_text("the key of another app")
    page = client.get("/setup/github-app/").content.decode()
    assert 'data-registration-blocked="PrivateKeyFileExists"' in page
    assert str(tmp_path / "github-app.pem") in page
    assert 'name="setup_code"' not in page
    response = start(client)
    assert response.status_code == 409
    assert 'data-registration-blocked="PrivateKeyFileExists"' in response.content.decode()
    assert (tmp_path / "github-app.pem").read_text() == "the key of another app"


@pytest.mark.parametrize("name", app_registration.ENVIRONMENT_NAMES)
def test_settings_of_an_app_in_the_environment_stop_the_registration(
    client, new_site, monkeypatch, name
):
    monkeypatch.setenv(name, "set")
    monkeypatch.setenv("GITHUB_SECRET", "set")
    expected = ", ".join(
        n for n in app_registration.ENVIRONMENT_NAMES if n in (name, "GITHUB_SECRET")
    )
    for url in ("/setup/github-app/", "/accounts/login/"):
        page = client.get(url).content.decode()
        assert 'data-registration-blocked="AppSettingsInEnvironment"' in page, url
        assert f"<code>{expected}</code>" in page, url
        assert 'href="/setup/github-app/">Register GitHub App</a>' not in page, url
        assert 'name="setup_code"' not in page, url
    response = start(client)  # a form sent anyway
    assert response.status_code == 409
    assert 'data-registration-blocked="AppSettingsInEnvironment"' in response.content.decode()


def test_the_log_says_why_the_app_cannot_be_registered(new_site, monkeypatch, capsys):
    from django.core.management import call_command

    monkeypatch.setenv("GITHUB_CLIENT_ID", "set")
    call_command("prepare")
    out = capsys.readouterr().out
    assert "cannot register one" in out
    assert "GITHUB_CLIENT_ID" in out
    assert "setup code" not in out
    call_command("github_app_setup_code")
    assert "GITHUB_CLIENT_ID" in capsys.readouterr().out


def test_empty_settings_of_the_environment_count_as_unset(client, new_site, monkeypatch):
    for name in app_registration.ENVIRONMENT_NAMES:
        monkeypatch.setenv(name, "")
    page = client.get("/accounts/login/").content.decode()
    assert 'href="/setup/github-app/">Register GitHub App</a>' in page
    assert "data-registration-blocked" not in page
    assert start(client).status_code == 200


def test_the_setup_code_is_needed(client, new_site):
    response = start(client, setup_code="wrong")
    assert response.status_code == 403
    assert 'data-error="SetupCodeWrong"' in response.content.decode()
    assert SESSION_KEY not in client.session


def test_development_needs_no_setup_code(client, new_site):
    new_site.DEBUG = True
    assert 'name="setup_code"' not in client.get("/setup/github-app/").content.decode()
    assert start(client, setup_code="").status_code == 200


@pytest.mark.parametrize(
    ("fields", "error"),
    [
        ({"name": ""}, "InvalidAppName"),
        ({"name": "x" * 35}, "InvalidAppName"),
        ({"organization": "bad/owner"}, "InvalidOrganization"),
    ],
)
def test_wrong_details(client, new_site, fields, error):
    response = start(client, **fields)
    assert response.status_code == 400
    assert f'data-error="{error}"' in response.content.decode()


def test_one_app_per_site(client, new_site):
    new_site.GITHUB_APP_ID = "1"
    page = client.get("/setup/github-app/").content.decode()
    assert 'data-registered="environment"' in page
    assert 'name="setup_code"' not in page


def test_a_local_site_is_registered_without_a_webhook(client, new_site):
    new_site.SITE_URL = "http://localhost:5000"
    assert "data-local" in client.get("/setup/github-app/").content.decode()
    page = start(client).content.decode()
    manifest = json.loads(unescape(page.split('name="manifest" value="')[1].split('"')[0]))
    assert "hook_attributes" not in manifest
    assert "default_events" not in manifest
    assert manifest["callback_urls"] == ["http://localhost:5000/accounts/github/login/callback/"]


def test_a_return_of_another_browser_is_refused(client, new_site, github):
    start(client)
    github.manifest_codes["c"] = dict(NEW_APP)
    response = client.get("/setup/github-app/registered/?code=c&state=forged")
    assert response.status_code == 400
    assert 'data-error="RegistrationExpired"' in response.content.decode()
    assert "c" in github.manifest_codes  # the code was not used


def test_a_return_without_code(client, new_site):
    start(client)
    response = client.get(f"/setup/github-app/registered/?state={client.session[SESSION_KEY]}")
    assert 'data-error="RegistrationCodeMissing"' in response.content.decode()


def test_the_error_of_github_can_be_copied(client, new_site):
    start(client)
    response = client.get(
        f"/setup/github-app/registered/?code=used&state={client.session[SESSION_KEY]}"
    )
    assert response.status_code == 502
    page = response.content.decode()
    details = unescape(page.split('id="error-details"')[1].split("</textarea>")[0])
    assert "Error: ManifestConversionFailed (HTTP 502)" in details
    assert "POST /app-manifests/used/conversions: 404 Not Found" in details
    assert "Page: /setup/github-app/registered/?code=used" in details
    assert "registration.ManifestConversionFailed" in details
    assert not (new_site.DATA_DIR / ".env").exists()


def test_a_volume_that_is_not_writable(client, new_site, github, monkeypatch):
    def refuse(*args):
        raise PermissionError("read-only file system")

    monkeypatch.setattr(registered_settings, "write_private", refuse)
    monkeypatch.setattr(AppRegistration, "setup_code", staticmethod(lambda: "code"))
    start(client)
    github.manifest_codes["c"] = dict(NEW_APP)
    response = client.get(
        f"/setup/github-app/registered/?code=c&state={client.session[SESSION_KEY]}"
    )
    assert response.status_code == 500
    assert "read-only file system" in response.content.decode()


def test_gunicorn_workers_are_restarted(monkeypatch, rf):
    sent = []
    monkeypatch.setattr(app_registration.os, "kill", lambda pid, sig: sent.append((pid, sig)))
    request = rf.get("/", SERVER_SOFTWARE="gunicorn/23.0.0")
    assert AppRegistration.reload_workers(request)
    assert sent == [(os.getppid(), signal.SIGHUP)]
    assert not AppRegistration.reload_workers(rf.get("/"))


def test_the_setup_code_is_in_the_log_and_the_command(new_site, capsys):
    from django.core.management import call_command

    call_command("prepare")
    code = AppRegistration.setup_code()
    assert f"/setup/github-app/ with the setup code {code}" in capsys.readouterr().out
    call_command("github_app_setup_code")
    assert capsys.readouterr().out.strip() == code
    new_site.GITHUB_APP_ID = "1"
    call_command("github_app_setup_code")
    assert "no code is needed" in capsys.readouterr().out


def test_without_an_app_the_errors_and_setup_offer_the_registration(client, new_site):
    setup = client.get("/setup/", follow=True).content.decode()  # signs in first
    assert 'href="/setup/github-app/">Register GitHub App</a>' in setup
    response = client.post("/accounts/github/login/")
    assert 'href="/setup/github-app/">Register GitHub App</a>' in response.content.decode()
