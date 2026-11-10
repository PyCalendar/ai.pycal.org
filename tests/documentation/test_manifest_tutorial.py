"""Execute the documented manifest workflow with fake GitHub responses."""

import getpass
import html
import json
import os
import re
import textwrap
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from ai_pycal.github.permissions import manifest

GUIDE = Path(__file__).parents[2] / "docs/how-to/github-app-manifest.rst"
EXAMPLES = [
    textwrap.dedent(code)
    for code in re.findall(
        r"^   uv run python - <<'PY'\n(.*?)^   PY$", GUIDE.read_text(), re.M | re.S
    )
]


@pytest.fixture
def registration_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    data = tmp_path / "data"
    data.mkdir()
    specification = manifest('An app with "quotes" <and> & characters', "http://localhost:5000")
    (data / "github-app-manifest.json").write_text(json.dumps(specification))
    return data, specification


def execute_example(number):
    previous = os.umask(0o022)
    try:
        exec(compile(EXAMPLES[number], str(GUIDE), "exec"), {})
    finally:
        os.umask(previous)


@pytest.mark.parametrize("organization", ["", "PyCalendar"])
def test_registration_form_preserves_manifest_and_escapes_html(registration_files, organization):
    data, specification = registration_files
    assert len(EXAMPLES) == 2
    code = EXAMPLES[0].replace('organization = ""', f'organization = "{organization}"')
    exec(compile(code, str(GUIDE), "exec"), {})
    form = (data / "github-app-register.html").read_text()
    submitted = html.unescape(re.search(r'name="manifest" value="([^"]*)"', form).group(1))
    assert json.loads(submitted) == specification
    assert "<and>" not in form
    assert "<script" not in form
    action = html.unescape(re.search(r'action="([^"]*)"', form).group(1))
    parsed = urlsplit(action)
    expected = (
        "/organizations/PyCalendar/settings/apps/new" if organization else "/settings/apps/new"
    )
    assert parsed.scheme == "https" and parsed.netloc == "github.com" and parsed.path == expected
    state = parse_qs(parsed.query)["state"][0]
    assert state == (data / "github-app-state.txt").read_text()
    assert len(state) >= 32


def test_credentials_example_checks_state_and_maps_github_fields(
    registration_files, monkeypatch, capsys
):
    data, _ = registration_files
    execute_example(0)
    state = (data / "github-app-state.txt").read_text()
    monkeypatch.setattr(
        getpass, "getpass", lambda _: f"http://localhost:5000/?code=temporary-code&state={state}"
    )
    credentials = {
        "id": 123,
        "slug": "my-app",
        "client_id": "client-id",
        "client_secret": "private-client-secret",
        "webhook_secret": "private-webhook-secret",
        "pem": "-----BEGIN PRIVATE KEY-----\nprivate-key\n-----END PRIVATE KEY-----\n",
    }
    calls = []

    def convert(url, **kwargs):
        calls.append((url, kwargs))
        return httpx.Response(201, json=credentials)

    monkeypatch.setattr(httpx, "post", convert)
    execute_example(1)
    assert len(calls) == 1
    assert calls[0][0] == "https://api.github.com/app-manifests/temporary-code/conversions"
    assert calls[0][1]["headers"]["Accept"] == "application/vnd.github+json"
    assert (data / "github-app.pem").read_text() == credentials["pem"]
    configured = dict(
        line.split("=", 1) for line in (data / "github-app-settings.env").read_text().splitlines()
    )
    assert configured == {
        "GITHUB_APP_ID": "123",
        "GITHUB_APP_SLUG": "my-app",
        "GITHUB_CLIENT_ID": "client-id",
        "GITHUB_SECRET": "private-client-secret",
        "GITHUB_WEBHOOK_SECRET": "private-webhook-secret",
        "GITHUB_APP_PRIVATE_KEY_FILE": "data/github-app.pem",
    }
    assert (data / "github-app.pem").stat().st_mode & 0o777 == 0o600
    assert (data / "github-app-settings.env").stat().st_mode & 0o777 == 0o600
    output = capsys.readouterr().out
    assert "private-key" not in output and "private-client-secret" not in output


@pytest.mark.parametrize(
    "query",
    [
        "code=temporary-code&state=wrong",
        "code=temporary-code",
        "state=valid",
        "code=a&code=b&state=valid",
    ],
)
def test_invalid_callback_is_rejected_without_exchanging_credentials(
    registration_files, monkeypatch, query
):
    data, _ = registration_files
    (data / "github-app-state.txt").write_text("valid")
    monkeypatch.setattr(getpass, "getpass", lambda _: f"http://localhost:5000/?{query}")
    calls = []
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: calls.append(args))
    with pytest.raises(SystemExit):
        execute_example(1)
    assert not calls
    assert not (data / "github-app.pem").exists()


def test_existing_key_is_preserved_before_the_one_time_code_is_used(
    registration_files, monkeypatch
):
    data, _ = registration_files
    key = data / "github-app.pem"
    key.write_text("existing private key")
    calls = []
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: calls.append(args))
    with pytest.raises(SystemExit):
        execute_example(1)
    assert not calls
    assert key.read_text() == "existing private key"


def test_conversion_failure_does_not_write_credentials(registration_files, monkeypatch):
    data, _ = registration_files
    (data / "github-app-state.txt").write_text("valid")
    monkeypatch.setattr(
        getpass, "getpass", lambda _: "http://localhost:5000/?code=expired&state=valid"
    )
    monkeypatch.setattr(
        httpx, "post", lambda *args, **kwargs: httpx.Response(404, json={"message": "Not found"})
    )
    with pytest.raises(SystemExit, match="GitHub rejected"):
        execute_example(1)
    assert not (data / "github-app.pem").exists()
