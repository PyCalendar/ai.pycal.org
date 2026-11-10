"""The GitHub App: it reads repositories and labels pull requests."""

import threading
import time
from datetime import datetime

import jwt
from django.conf import settings

from ai_pycal.errors import GitHubAppNotConfigured, InstallationNotFound, InvalidPrivateKey
from ai_pycal.errors.github import GitHubNotFound

from .client import GitHubClient


class GitHubApp:
    """The GitHub App of the site, configured with ``GITHUB_APP_ID`` and its private key."""

    # installation id: (token, expiry as a timestamp); tokens are valid for an hour
    _tokens: dict[int, tuple[str, float]] = {}
    _lock = threading.Lock()

    @staticmethod
    def configured() -> bool:
        """Whether the GitHub App is set up.

        Returns:
            True if the id and the private key are set.
        """
        return bool(settings.GITHUB_APP_ID and settings.GITHUB_APP_PRIVATE_KEY)

    @classmethod
    def jwt(cls) -> str:
        """The token with which the app speaks for itself, valid for nine minutes.

        Returns:
            The JSON Web Token.

        Raises:
            GitHubAppNotConfigured: There is no app.
            InvalidPrivateKey: The key can not sign.
        """
        if not cls.configured():
            raise GitHubAppNotConfigured("GITHUB_APP_ID, GITHUB_APP_PRIVATE_KEY")
        now = int(time.time())
        payload = {"iat": now - 60, "exp": now + 540, "iss": str(settings.GITHUB_APP_ID)}
        try:
            return jwt.encode(payload, settings.GITHUB_APP_PRIVATE_KEY, algorithm="RS256")
        except (ValueError, TypeError, jwt.PyJWTError) as error:
            raise InvalidPrivateKey(str(error)) from error

    @classmethod
    def app_client(cls) -> GitHubClient:
        """A client that speaks for the app itself.

        Returns:
            The client.
        """
        return GitHubClient(cls.jwt())

    @classmethod
    def installation_token(cls, installation_id: int) -> str:
        """A token of an installation, kept until shortly before it expires.

        Args:
            installation_id: The id of the installation on GitHub.

        Returns:
            The token.

        Raises:
            InstallationNotFound: The app is not installed there.
        """
        with cls._lock:
            cached = cls._tokens.get(installation_id)
            if cached and cached[1] > time.time() + 60:
                return cached[0]
        try:
            data = cls.app_client().json(
                "POST", f"/app/installations/{installation_id}/access_tokens"
            )
        except GitHubNotFound as error:
            raise InstallationNotFound(str(installation_id)) from error
        expires = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00")).timestamp()
        with cls._lock:
            cls._tokens[installation_id] = (data["token"], expires)
        return data["token"]

    @classmethod
    def for_installation(cls, installation_id: int) -> GitHubClient:
        """A client with the rights of an installation.

        Args:
            installation_id: The id of the installation on GitHub.

        Returns:
            The client.
        """
        return GitHubClient(cls.installation_token(installation_id))

    @classmethod
    def installation(cls, installation_id: int) -> dict:
        """What GitHub knows about an installation, with its permissions.

        Args:
            installation_id: The id of the installation on GitHub.

        Returns:
            The installation as GitHub describes it.

        Raises:
            InstallationNotFound: The app is not installed there.
        """
        try:
            return cls.app_client().get(f"/app/installations/{installation_id}")
        except GitHubNotFound as error:
            raise InstallationNotFound(str(installation_id)) from error

    @classmethod
    def forget_tokens(cls) -> None:
        """Forget the tokens of the installations, such as between tests."""
        with cls._lock:
            cls._tokens.clear()

    @staticmethod
    def install_url() -> str:
        """The page of GitHub on which people install the app.

        Returns:
            The address; "" without ``GITHUB_APP_SLUG``.
        """
        slug = settings.GITHUB_APP_SLUG
        return f"https://github.com/apps/{slug}/installations/new" if slug else ""
