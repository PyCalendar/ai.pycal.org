"""A local site behind a public HTTPS tunnel, such as Tailscale Funnel, for webhooks."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from allauth.utils import build_absolute_uri
from django.test import RequestFactory

from ai_pycal.development import configure_environment
from ai_pycal.github.permissions import manifest

ROOT = Path(__file__).parents[2]
TUNNEL = "https://laptop.tail1234.ts.net"


def test_the_tunnel_address_is_allowed_and_trusted():
    environment = {"SITE_URL": TUNNEL}
    configure_environment(environment)
    assert environment["ALLOWED_HOSTS"].split(",")[0] == "laptop.tail1234.ts.net"
    assert environment["CSRF_TRUSTED_ORIGINS"] == TUNNEL
    assert "localhost" in environment["ALLOWED_HOSTS"].split(",")


def test_the_manifest_points_github_to_the_tunnel():
    app = manifest("sign.pycal.org local", TUNNEL)
    assert app["hook_attributes"] == {"url": f"{TUNNEL}/github/webhook/", "active": True}
    assert app["callback_urls"] == [f"{TUNNEL}/accounts/github/login/callback/"]
    assert app["setup_url"] == f"{TUNNEL}/setup/installed/"


@pytest.mark.parametrize(
    ("site_url", "protocol"), [(TUNNEL, "https"), ("http://localhost:5000", "http")]
)
def test_the_sign_in_callback_uses_the_scheme_of_the_site_url(site_url, protocol):
    environment = dict(os.environ, SITE_URL=site_url, DEBUG="1")
    environment["DJANGO_SETTINGS_MODULE"] = "ai_pycal.settings"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from django.conf import settings; print(settings.ACCOUNT_DEFAULT_HTTP_PROTOCOL)",
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == protocol


def test_the_callback_is_https_without_x_forwarded_proto(settings):
    settings.ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"
    request = RequestFactory().get("/", HTTP_HOST="laptop.tail1234.ts.net")
    assert not request.is_secure()
    url = build_absolute_uri(request, "/accounts/github/login/callback/")
    assert url == f"{TUNNEL}/accounts/github/login/callback/"


def test_the_guide_explains_the_tunnel():
    text = " ".join((ROOT / "docs" / "how-to" / "github-app-tunnel.rst").read_text().split())
    for needed in (
        "tailscale funnel",
        "SITE_URL=https://",
        "/github/webhook/",
        "Recent Deliveries",
    ):
        assert needed in text, needed
    assert "github-app-tunnel" in (ROOT / "docs" / "how-to" / "github-app.rst").read_text()
