"""Renew GitHub user tokens without making network requests."""

from datetime import timedelta
from urllib.parse import parse_qs

import httpx
import pytest
from allauth.socialaccount.models import SocialApp, SocialToken
from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from django.utils import timezone

from ai_pycal.errors import GitHubLoginExpired
from ai_pycal.services.identity import GitHubIdentity

pytestmark = pytest.mark.django_db


@pytest.fixture
def expired_token(maintainer):
    token = SocialToken.objects.get(account__user=maintainer)
    token.token = "expired"
    token.token_secret = "refresh-token"
    token.expires_at = timezone.now() - timedelta(seconds=1)
    token.save()
    return token


def renewals(github):
    return [r for r in github.requests if r.url.path == "/login/oauth/access_token"]


def test_allauth_keeps_the_refresh_token_and_expiry():
    before = timezone.now()
    token = GitHubOAuth2Adapter(None).parse_token(
        {"access_token": "user-token", "refresh_token": "refresh-token", "expires_in": 28800}
    )
    assert token.token_secret == "refresh-token"
    assert before + timedelta(hours=8) <= token.expires_at <= timezone.now() + timedelta(hours=8)


@pytest.mark.parametrize("remaining", [None, 3600])
def test_valid_and_nonexpiring_tokens_are_used_without_refresh(maintainer, github, remaining):
    token = SocialToken.objects.get(account__user=maintainer)
    token.expires_at = timezone.now() + timedelta(seconds=remaining) if remaining else None
    token.save()
    assert GitHubIdentity.token(maintainer) == "user-token"
    assert not github.requests


def test_a_missing_token_is_still_empty(alice, github):
    assert GitHubIdentity.token(alice) == ""
    assert not github.requests


@pytest.mark.parametrize("remaining", [-1, 30])
def test_setup_renews_tokens_before_using_them(
    client, example, maintainer, expired_token, remaining
):
    expired_token.expires_at = timezone.now() + timedelta(seconds=remaining)
    expired_token.save()
    client.force_login(maintainer)
    before = timezone.now()
    response = client.get("/setup/installed/?installation_id=1")
    assert response.status_code == 302
    expired_token.refresh_from_db()
    assert expired_token.token == "user-token"
    assert expired_token.token_secret == "refresh-token-next"
    assert before + timedelta(hours=8) <= expired_token.expires_at
    requests = renewals(example)
    assert len(requests) == 1
    assert str(requests[0].url) == "https://github.com/login/oauth/access_token"
    assert parse_qs(requests[0].content.decode()) == {
        "client_id": ["client"],
        "client_secret": ["secret"],
        "grant_type": ["refresh_token"],
        "refresh_token": ["refresh-token"],
    }
    assert requests[0].headers["Accept"] == "application/json"
    assert not requests[0].url.query
    client.get("/setup/")
    assert len(renewals(example)) == 1
    # The next expiry must exchange the replacement, not the invalidated token.
    expired_token.expires_at = timezone.now() - timedelta(seconds=1)
    expired_token.save()
    assert GitHubIdentity.token(maintainer) == "user-token"
    expired_token.refresh_from_db()
    assert expired_token.token_secret == "refresh-token-next-next"


def test_refresh_uses_the_app_that_issued_the_token(maintainer, expired_token, settings, github):
    app = SocialApp.objects.create(provider="github", client_id="client", secret="secret")
    expired_token.app = app
    expired_token.save()
    settings.SOCIALACCOUNT_PROVIDERS = {
        "github": {"APP": {"client_id": "other", "secret": "other"}}
    }
    assert GitHubIdentity.token(maintainer) == "user-token"


def test_expired_token_without_a_refresh_requires_login(maintainer, expired_token, github):
    expired_token.token_secret = ""
    expired_token.save()
    with pytest.raises(GitHubLoginExpired):
        GitHubIdentity.token(maintainer)
    assert not github.requests


def test_rejected_refresh_shows_the_login_error(client, example, maintainer, expired_token):
    example.refresh_tokens.clear()
    client.force_login(maintainer)
    response = client.get("/setup/installed/?installation_id=1")
    assert response.status_code == 401
    assert b'data-error="GitHubLoginExpired"' in response.content
    assert b"errors.html#ai_pycal.errors.github.GitHubLoginExpired" in response.content
    expired_token.refresh_from_db()
    assert expired_token.token == "expired"
    assert expired_token.token_secret == "refresh-token"


@pytest.mark.parametrize(
    ("response", "error", "status"),
    [
        (httpx.Response(200, json=[]), "GitHubTokenResponseInvalid", 502),
        (httpx.Response(200, json={}), "GitHubTokenResponseInvalid", 502),
        (httpx.Response(200, text="secret"), "GitHubAnswerNotJSON", 502),
        (
            httpx.Response(200, json={"error": "incorrect_client_credentials"}),
            "SignInNotConfigured",
            503,
        ),
        (
            httpx.Response(200, json={"error": "unexpected", "error_description": "secret"}),
            "GitHubError",
            502,
        ),
        (httpx.Response(401, json={"message": "secret"}), "GitHubError", 502),
        (httpx.Response(503, text="secret"), "GitHubError", 502),
        (httpx.Response(429, text="secret"), "GitHubRateLimited", 503),
    ],
)
def test_refresh_errors_are_visible_and_preserve_credentials(
    client, example, maintainer, expired_token, response, error, status
):
    example.oauth_response = response
    client.force_login(maintainer)
    page = client.get("/setup/installed/?installation_id=1")
    assert page.status_code == status
    assert f'data-error="{error}"'.encode() in page.content
    assert b"secret" not in page.content
    assert b"refresh-token" not in page.content
    expired_token.refresh_from_db()
    assert expired_token.token == "expired"
    assert expired_token.token_secret == "refresh-token"


@pytest.mark.parametrize("field", ["access_token", "refresh_token", "expires_in"])
@pytest.mark.parametrize("value", [None, "", 0, -1, [], True])
def test_invalid_replacements_do_not_overwrite_tokens(
    client, example, maintainer, expired_token, field, value
):
    data = {"access_token": "new-access", "refresh_token": "new-refresh", "expires_in": 28800}
    data[field] = value
    example.oauth_response = httpx.Response(200, json=data)
    client.force_login(maintainer)
    response = client.get("/setup/installed/?installation_id=1")
    assert response.status_code == 502
    assert b'data-error="GitHubTokenResponseInvalid"' in response.content
    expired_token.refresh_from_db()
    assert expired_token.token == "expired"
    assert expired_token.token_secret == "refresh-token"


def test_unreachable_refresh_is_retryable(client, example, maintainer, expired_token):
    example.unreachable = True
    client.force_login(maintainer)
    response = client.get("/setup/installed/?installation_id=1")
    assert response.status_code == 503
    assert b'data-error="GitHubUnreachable"' in response.content
    example.unreachable = False
    assert client.get("/setup/installed/?installation_id=1").status_code == 302


@pytest.mark.parametrize("app", [None, {"client_id": "client", "secret": ""}])
def test_missing_client_credentials_have_a_setup_error(
    client, example, maintainer, expired_token, settings, app
):
    settings.SOCIALACCOUNT_PROVIDERS = {"github": {"APP": app} if app else {}}
    client.force_login(maintainer)
    response = client.get("/setup/installed/?installation_id=1")
    assert response.status_code == 503
    assert b'data-error="SignInNotConfigured"' in response.content
    assert not renewals(example)
