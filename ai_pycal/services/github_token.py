"""Renew the GitHub user tokens used to administer repositories."""

from datetime import timedelta

import httpx
from allauth.socialaccount.adapter import get_adapter
from allauth.socialaccount.models import SocialApp, SocialToken
from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from django.db import transaction
from django.utils import timezone

from ai_pycal.errors import (
    GitHubAnswerNotJSON,
    GitHubError,
    GitHubLoginExpired,
    GitHubRateLimited,
    GitHubTokenResponseInvalid,
    GitHubUnreachable,
    SignInNotConfigured,
)
from ai_pycal.github.client import GitHubClient


class GitHubUserToken:
    """Keep access and refresh tokens together when GitHub rotates them."""

    @classmethod
    def for_user(cls, user) -> str:
        """Get a token, renewing it when fewer than sixty seconds remain.

        Args:
            user: The signed-in user whose GitHub installations will be requested.

        Returns:
            The access token, or an empty string when none was stored.

        Raises:
            GitHubLoginExpired: The expired token cannot be renewed; sign in again.
            GitHubError: GitHub could not renew the token; try again later.
        """
        # GitHub invalidates a refresh token on use. Lock before reading it so
        # simultaneous requests cannot both try to exchange the same token.
        with transaction.atomic():
            token = (
                SocialToken.objects.select_for_update()
                .filter(account__user=user, account__provider="github")
                .first()
            )
            if token is None:
                return ""
            if token.expires_at and token.expires_at <= timezone.now() + timedelta(seconds=60):
                cls.refresh(token)
            return token.token

    @staticmethod
    def refresh(token: SocialToken) -> None:
        """Exchange the refresh token and save both replacements atomically.

        Args:
            token: The stored token, locked by the caller's transaction.

        Raises:
            GitHubLoginExpired: GitHub rejected the refresh token, or it is missing.
            SignInNotConfigured: The GitHub App's client credentials are missing or invalid.
            GitHubUnreachable: The token endpoint could not be reached.
            GitHubRateLimited: GitHub allows no more requests for now.
            GitHubAnswerNotJSON: The token endpoint returned unreadable JSON.
            GitHubTokenResponseInvalid: The response lacks valid replacement credentials.
            GitHubError: GitHub returned another error.
        """
        if not token.token_secret:
            raise GitHubLoginExpired("No refresh token was stored; sign out and sign in again.")
        try:
            app = token.app if token.app_id else get_adapter().get_app(None, provider="github")
        except SocialApp.DoesNotExist as error:
            raise SignInNotConfigured() from error
        if not app.client_id or not app.secret:
            raise SignInNotConfigured()
        try:
            with GitHubClient().http as http:
                response = http.post(
                    GitHubOAuth2Adapter.access_token_url,
                    headers={"Accept": "application/json"},
                    data={
                        "client_id": app.client_id,
                        "client_secret": app.secret,
                        "grant_type": "refresh_token",
                        "refresh_token": token.token_secret,
                    },
                )
        except httpx.TransportError as error:
            # Neither exception messages nor OAuth responses are safe to show:
            # they may contain the credentials submitted to GitHub.
            raise GitHubUnreachable("GitHub token renewal could not be reached.") from error
        if response.status_code == 429 or response.headers.get("x-ratelimit-remaining") == "0":
            raise GitHubRateLimited("GitHub token renewal was rate limited.")
        if response.is_server_error:
            raise GitHubError(f"GitHub token renewal returned HTTP {response.status_code}.")
        try:
            data = response.json()
        except ValueError as error:
            raise GitHubAnswerNotJSON("GitHub token renewal returned unreadable JSON.") from error
        if not isinstance(data, dict):
            raise GitHubTokenResponseInvalid()
        if data.get("error") == "incorrect_client_credentials":
            raise SignInNotConfigured()
        if data.get("error") in ("bad_refresh_token", "invalid_grant", "expired_token"):
            raise GitHubLoginExpired("GitHub rejected token renewal; sign out and sign in again.")
        if not response.is_success or data.get("error"):
            raise GitHubError(f"GitHub token renewal failed (HTTP {response.status_code}).")
        access = data.get("access_token")
        refresh = data.get("refresh_token")
        seconds = data.get("expires_in")
        if (
            not isinstance(access, str)
            or not access
            or not isinstance(refresh, str)
            or not refresh
            or isinstance(seconds, bool)
            or not isinstance(seconds, (int, str))
        ):
            raise GitHubTokenResponseInvalid()
        try:
            lifetime = int(seconds)
            if lifetime <= 0:
                raise ValueError("nonpositive lifetime")
            expires_at = timezone.now() + timedelta(seconds=lifetime)
        except (ValueError, OverflowError) as error:
            raise GitHubTokenResponseInvalid() from error
        token.token = access
        token.token_secret = refresh
        token.expires_at = expires_at
        token.save(update_fields=["token", "token_secret", "expires_at"])
