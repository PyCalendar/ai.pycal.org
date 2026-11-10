"""Check real manifest output after the development entrypoint initializes settings."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]


@pytest.mark.parametrize(
    "port,configured_url", [(5000, None), (5123, None), (5000, "https://tunnel.example")]
)
def test_development_manifest_urls(tmp_path, port, configured_url):
    environment = dict(os.environ)
    for key in (
        "SITE_URL",
        "SITE_NAME",
        "DEBUG",
        "DOCS_URL",
        "ALLOWED_HOSTS",
        "CSRF_TRUSTED_ORIGINS",
    ):
        environment.pop(key, None)
    environment.update({"DATA_DIR": str(tmp_path), "SECRET_KEY": "test-development-manifest"})
    if configured_url:
        environment["SITE_URL"] = configured_url
    result = subprocess.run(
        [sys.executable, "-m", "ai_pycal.development", "--port", str(port), "app_manifest"],
        env=environment,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    manifest = json.loads(result.stdout)
    base = configured_url or f"http://localhost:{port}"
    assert manifest["url"] == base
    assert manifest["redirect_url"] == f"{base}/"
    assert manifest["callback_urls"] == [f"{base}/accounts/github/login/callback/"]
    assert manifest["setup_url"] == f"{base}/setup/installed/"
    assert manifest["hook_attributes"]["url"] == f"{base}/github/webhook/"
