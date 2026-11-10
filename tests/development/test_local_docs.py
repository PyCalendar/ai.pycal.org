"""Development commands apply shared defaults after dotenv without starting servers."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from ai_pycal.development import configure_environment

ROOT = Path(__file__).parents[2]
VARIABLES = ("DEBUG", "SITE_URL", "SITE_NAME", "ALLOWED_HOSTS", "CSRF_TRUSTED_ORIGINS", "DOCS_URL")
GITHUB_VARIABLES = (
    "GITHUB_APP_ID",
    "GITHUB_APP_SLUG",
    "GITHUB_CLIENT_ID",
    "GITHUB_SECRET",
    "GITHUB_WEBHOOK_SECRET",
    "GITHUB_APP_PRIVATE_KEY_FILE",
)


@pytest.fixture
def make_commands(tmp_path, monkeypatch):
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".env").write_text("")
    log = tmp_path / "commands.jsonl"
    fake_uv = tmp_path / "uv"
    fake_uv.write_text(f"""#!{sys.executable}
import json, os, sys
sys.path.insert(0, {str(ROOT)!r})
from environ import Env
argv = sys.argv[1:]
if '--env-file' in argv:
    Env.read_env(argv[argv.index('--env-file') + 1])
def record(command):
    with open(os.environ['MAKE_TEST_LOG'], 'a') as stream:
        stream.write(json.dumps({{'args': argv, 'command': command,
            'environment': {{key: os.environ.get(key) for key in {VARIABLES!r}}},
            'github_environment': {{key: os.environ.get(key) for key in {GITHUB_VARIABLES!r}}}}}) + '\\n')
if '-m' in argv:
    from django.core import management
    management.execute_from_command_line = record
    from ai_pycal.development import main
    main(argv[argv.index('-m') + 2:])
else:
    record(argv)
""")
    fake_uv.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("MAKE_TEST_LOG", str(log))
    for variable in (*VARIABLES, *GITHUB_VARIABLES, "PORT", "DOCS_PORT"):
        monkeypatch.delenv(variable, raising=False)

    def run(*targets, port=None, docs_port=None):
        command = ["make", "-f", str(ROOT / "Makefile")]
        if port:
            command.append(f"PORT={port}")
        if docs_port:
            command.append(f"DOCS_PORT={docs_port}")
        for target in targets:
            subprocess.run(command + [target], cwd=tmp_path, check=True, capture_output=True)
        return [json.loads(line) for line in log.read_text().splitlines()]

    return run


@pytest.mark.parametrize("port", [None, "8123"])
def test_run_and_livehtml_use_the_same_local_docs_port(make_commands, port):
    migration, run, docs = make_commands("run", "livehtml", docs_port=port)
    assert migration["args"][-1] == "migrate"
    assert run["command"] == ["manage.py", "runserver", "5000"]
    assert run["environment"]["DOCS_URL"] == f"http://localhost:{port or '8000'}/"
    assert run["environment"]["DEBUG"] == "1"
    assert "--env-file" in run["args"]
    assert docs["args"][docs["args"].index("--port") + 1] == (port or "8000")


def test_run_and_manifest_share_local_defaults(make_commands):
    _migration, run, manifest = make_commands("run", "app-manifest")
    assert (
        run["environment"]
        == manifest["environment"]
        == {
            "DEBUG": "1",
            "SITE_URL": "http://localhost:5000",
            "SITE_NAME": "localhost",
            "ALLOWED_HOSTS": "localhost,127.0.0.1,[::1]",
            "CSRF_TRUSTED_ORIGINS": "http://localhost:5000",
            "DOCS_URL": "http://localhost:8000/",
        }
    )
    assert manifest["command"] == ["manage.py", "app_manifest"]


@pytest.mark.parametrize("source", ["dotenv", "environment"])
def test_configured_values_take_precedence_over_development_defaults(
    make_commands, monkeypatch, tmp_path, source
):
    configured = {
        "DEBUG": "0",
        "SITE_NAME": "My development app",
        "SITE_URL": "https://dev.example",
        "ALLOWED_HOSTS": "dev.example",
        "CSRF_TRUSTED_ORIGINS": "https://trusted.example",
        "DOCS_URL": "https://docs.example/",
    }
    if source == "dotenv":
        (tmp_path / ".env").write_text(
            "\n".join(f"{key}={value}" for key, value in configured.items())
        )
    else:
        (tmp_path / ".env").write_text("SITE_URL=https://dotenv.example\n")
        for key, value in configured.items():
            monkeypatch.setenv(key, value)
    _migration, run, manifest = make_commands("run", "app-manifest")
    assert run["environment"] == configured
    assert manifest["environment"] == configured


def test_custom_port_is_used_in_both_run_and_manifest(make_commands):
    _migration, run, manifest = make_commands("run", "app-manifest", port="5123")
    assert run["command"][-1] == "5123"
    assert run["environment"]["SITE_URL"] == "http://localhost:5123"
    assert manifest["environment"]["SITE_URL"] == "http://localhost:5123"
    assert manifest["environment"]["CSRF_TRUSTED_ORIGINS"] == "http://localhost:5123"


def test_explicit_site_url_supplies_host_and_csrf_defaults():
    environment = {"SITE_URL": "https://tunnel.example:8443/", "GITHUB_CLIENT_ID": "keep-me"}
    configure_environment(environment)
    assert environment["SITE_NAME"] == "tunnel.example"
    assert environment["ALLOWED_HOSTS"] == "tunnel.example,localhost,127.0.0.1,[::1]"
    assert environment["CSRF_TRUSTED_ORIGINS"] == "https://tunnel.example:8443"
    assert environment["GITHUB_CLIENT_ID"] == "keep-me"


def test_empty_values_get_development_defaults():
    environment = dict.fromkeys(VARIABLES, "")
    configure_environment(environment)
    assert all(environment.values())
    assert environment["SITE_URL"] == "http://localhost:5000"


@pytest.mark.parametrize("port,docs_port", [("5000", "8000"), ("5123", "8123")])
def test_development_env_example_loads_credentials_and_keeps_port_defaults(
    make_commands, tmp_path, port, docs_port
):
    example = (ROOT / ".env.development.example").read_text()
    credentials = {name: f"test-{name.lower()}" for name in GITHUB_VARIABLES}
    credentials["GITHUB_APP_PRIVATE_KEY_FILE"] = "data/github-app.pem"
    lines = []
    for line in example.splitlines():
        name, separator, value = line.partition("=")
        if separator and name in credentials:
            line = f"{name}={credentials[name]}"
        lines.append(line)
    (tmp_path / ".env").write_text("\n".join(lines))
    _migration, run, manifest = make_commands("run", "app-manifest", port=port, docs_port=docs_port)
    assert run["github_environment"] == manifest["github_environment"] == credentials
    assert run["environment"] == manifest["environment"]
    assert run["environment"]["SITE_URL"] == f"http://localhost:{port}"
    assert run["environment"]["DOCS_URL"] == f"http://localhost:{docs_port}/"
    assert run["environment"]["SITE_NAME"] == "localhost"
