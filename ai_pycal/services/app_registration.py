"""Register the GitHub App of the site on the site itself, with a GitHub App manifest.

The people who run the site press *Register GitHub App* (``/setup/github-app/``). The site
builds the manifest for its own address, GitHub creates the app and returns a code, and the
site exchanges the code for the credentials and writes them into its volume
(``DATA_DIR/.env`` and ``DATA_DIR/github-app.pem``). A site has one app; the settings of the
environment take precedence over those of the volume.
"""

import hmac
import ipaddress
import os
import re
import secrets
import signal
from pathlib import Path
from urllib.parse import quote, urlsplit

from django.conf import settings

from ai_pycal import registered_settings
from ai_pycal.errors import (
    AppAlreadyRegistered,
    AppSettingsInEnvironment,
    GitHubError,
    GitHubUnreachable,
    InvalidAppName,
    InvalidOrganization,
    ManifestConversionFailed,
    PrivateKeyFileExists,
    RegistrationCodeMissing,
    RegistrationExpired,
    RegistrationNotSaved,
    SetupCodeWrong,
)
from ai_pycal.github.client import GitHubClient
from ai_pycal.github.permissions import manifest

LOGIN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?")
SESSION_KEY = "github_app_registration"
# set in the environment, they would take precedence over the registered app
ENVIRONMENT_NAMES = (
    "GITHUB_APP_ID",
    "GITHUB_APP_SLUG",
    "GITHUB_CLIENT_ID",
    "GITHUB_SECRET",
    "GITHUB_WEBHOOK_SECRET",
    "GITHUB_APP_PRIVATE_KEY",
)
NAMES = (
    "GITHUB_APP_ID",
    "GITHUB_APP_SLUG",
    "GITHUB_CLIENT_ID",
    "GITHUB_SECRET",
    "GITHUB_WEBHOOK_SECRET",
    "GITHUB_APP_PRIVATE_KEY_FILE",
)


class AppRegistration:
    """The registration of the one GitHub App of the site."""

    @staticmethod
    def env_file() -> Path:
        """The settings that the registration writes: ``DATA_DIR/.env``."""
        return settings.DATA_DIR / ".env"

    @staticmethod
    def key_file() -> Path:
        """The file of the private key that the registration writes.

        Returns:
            ``GITHUB_APP_PRIVATE_KEY_FILE`` of the environment if it is set, such as
            ``/app/data/github-app.pem`` of ``.env.example``; else
            ``DATA_DIR/github-app.pem``.
        """
        configured = os.environ.get("GITHUB_APP_PRIVATE_KEY_FILE", "")
        return Path(configured) if configured else settings.DATA_DIR / "github-app.pem"

    @staticmethod
    def code_file() -> Path:
        """The setup code that allows the registration: ``DATA_DIR/github-app-setup-code``."""
        return settings.DATA_DIR / "github-app-setup-code"

    @classmethod
    def source(cls) -> str:
        """Where the GitHub App of the site is configured.

        Returns:
            ``environment``, ``volume`` (registered on the site), or "" without an app.
        """
        if not settings.GITHUB_APP_ID:
            return ""
        registered = registered_settings.read(cls.env_file())
        if registered.get("GITHUB_APP_ID") == str(settings.GITHUB_APP_ID):
            return "volume"
        return "environment"

    @staticmethod
    def is_local(url: str) -> bool:
        """Whether GitHub cannot reach the address, such as ``http://localhost:5000``.

        Args:
            url: The address of the site.

        Returns:
            True for localhost, ``.local`` names and private or loopback addresses.

        Examples:
            >>> AppRegistration.is_local("http://localhost:5000")
            True
            >>> AppRegistration.is_local("http://192.168.1.5:5000")
            True
            >>> AppRegistration.is_local("https://laptop.tail1234.ts.net")
            False
        """
        host = (urlsplit(url).hostname or "").lower()
        if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
            return True
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            return False
        return address.is_private or address.is_loopback or address.is_link_local

    @classmethod
    def manifest(cls, name: str) -> dict:
        """The manifest of the app for the address of this site.

        GitHub returns to ``/setup/github-app/registered/``. GitHub cannot deliver
        webhooks to a local address, so the app of a local site has none; add the
        webhook in the settings of the app when the site has a public address.

        Args:
            name: The name of the app on GitHub.

        Returns:
            The manifest.
        """
        found = manifest(name, settings.SITE_URL)
        found["redirect_url"] = f"{settings.SITE_URL}/setup/github-app/registered/"
        if cls.is_local(settings.SITE_URL):
            found.pop("hook_attributes")
            found.pop("default_events")
        return found

    @staticmethod
    def check_name(name: str) -> str:
        """The name of the app, checked.

        Args:
            name: The name entered.

        Returns:
            The name without spaces around it.

        Raises:
            InvalidAppName: Empty or longer than 34 characters.
        """
        name = name.strip()
        if not name or len(name) > 34:
            raise InvalidAppName(name)
        return name

    @staticmethod
    def check_organization(organization: str) -> str:
        """The organization, checked.

        Args:
            organization: The login entered; "" for the own account.

        Returns:
            The login.

        Raises:
            InvalidOrganization: Not a GitHub login.
        """
        organization = organization.strip()
        if organization and not LOGIN.fullmatch(organization):
            raise InvalidOrganization(organization)
        return organization

    @staticmethod
    def github_url(organization: str, state: str) -> str:
        """The page of GitHub that receives the manifest.

        Args:
            organization: The login of the organization; "" for the own account.
            state: The secret of this registration.

        Returns:
            The address, such as ``https://github.com/settings/apps/new?state=...``.

        Examples:
            >>> AppRegistration.github_url("PyCalendar", "s")
            'https://github.com/organizations/PyCalendar/settings/apps/new?state=s'
        """
        page = (
            f"https://github.com/organizations/{quote(organization, safe='')}/settings/apps/new"
            if organization
            else "https://github.com/settings/apps/new"
        )
        return f"{page}?state={quote(state, safe='')}"

    @classmethod
    def setup_code(cls) -> str:
        """The setup code that allows the registration, created once.

        Returns:
            Such as ``3f9a-0c41-77d2``.
        """
        path = cls.code_file()
        if path.is_file():
            return path.read_text().strip()
        code = "-".join(secrets.token_hex(2) for _ in range(3))
        path.parent.mkdir(parents=True, exist_ok=True)
        registered_settings.write_private(path, code + "\n")
        return code

    @classmethod
    def needs_setup_code(cls) -> bool:
        """Whether the page asks for the setup code: always, except in development."""
        return not settings.DEBUG

    @classmethod
    def check(cls, setup_code: str) -> None:
        """Check that a registration may start.

        Args:
            setup_code: The code entered.

        Raises:
            AppAlreadyRegistered: The site has an app.
            AppSettingsInEnvironment: The environment sets some settings of an app.
            PrivateKeyFileExists: The key would overwrite a file.
            SetupCodeWrong: The code is not that of the site.
        """
        if cls.source():
            raise AppAlreadyRegistered(cls.source())
        found = [name for name in ENVIRONMENT_NAMES if os.environ.get(name)]
        if found:
            raise AppSettingsInEnvironment(", ".join(found))
        if cls.key_file().exists():
            raise PrivateKeyFileExists(str(cls.key_file()))
        if cls.needs_setup_code() and not hmac.compare_digest(
            setup_code.strip().lower(), cls.setup_code().lower()
        ):
            raise SetupCodeWrong()

    @classmethod
    def start(cls, session, name: str, organization: str, setup_code: str) -> dict:
        """Start a registration: the form that sends the manifest to GitHub.

        Args:
            session: The session of the browser; it keeps the state.
            name: The name of the app.
            organization: The organization; "" for the own account.
            setup_code: The setup code entered.

        Returns:
            ``action`` (the page of GitHub), ``manifest`` and ``organization``.
        """
        cls.check(setup_code)
        name = cls.check_name(name)
        organization = cls.check_organization(organization)
        state = secrets.token_urlsafe(32)
        session[SESSION_KEY] = state
        return {
            "action": cls.github_url(organization, state),
            "manifest": cls.manifest(name),
            "organization": organization,
        }

    @classmethod
    def finish(cls, session, code: str, state: str) -> dict:
        """Exchange the code of GitHub for the credentials and save them.

        Args:
            session: The session of the browser, with the state of the registration.
            code: ``code`` of the return from GitHub.
            state: ``state`` of the return from GitHub.

        Returns:
            The answer of GitHub about the new app, without its secrets.

        Raises:
            AppAlreadyRegistered: The site has an app.
            RegistrationExpired: The state is not that of this browser.
            RegistrationCodeMissing: GitHub returned without a code.
            ManifestConversionFailed: GitHub refused the code.
        """
        if cls.source():
            raise AppAlreadyRegistered(cls.source())
        expected = session.get(SESSION_KEY, "")
        if not expected or not hmac.compare_digest(expected, state or ""):
            raise RegistrationExpired(
                "the state of the return from GitHub is not that of this browser's registration"
            )
        if not code:
            raise RegistrationCodeMissing()
        session.pop(SESSION_KEY, None)
        try:
            answer = (
                GitHubClient()
                .request("POST", f"/app-manifests/{quote(code, safe='')}/conversions")
                .json()
            )
        except GitHubUnreachable:
            raise
        except GitHubError as error:
            raise ManifestConversionFailed(str(error)) from error
        cls.save(answer)
        return {
            key: answer.get(key)
            for key in ("id", "slug", "name", "html_url", "owner", "permissions", "events")
        }

    @classmethod
    def save(cls, answer: dict) -> None:
        """Write the credentials into the volume and use them at once.

        Args:
            answer: The answer of GitHub to the conversion of the code.

        Raises:
            PrivateKeyFileExists: The file of the key appeared meanwhile.
            RegistrationNotSaved: The volume is not writable.
        """
        values = {
            "GITHUB_APP_ID": str(answer["id"]),
            "GITHUB_APP_SLUG": answer["slug"],
            "GITHUB_CLIENT_ID": answer["client_id"],
            "GITHUB_SECRET": answer["client_secret"],
            "GITHUB_WEBHOOK_SECRET": answer.get("webhook_secret") or "",
            "GITHUB_APP_PRIVATE_KEY_FILE": str(cls.key_file()),
        }
        if cls.key_file().exists():
            raise PrivateKeyFileExists(str(cls.key_file()))
        try:
            settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
            cls.key_file().parent.mkdir(parents=True, exist_ok=True)
            registered_settings.write_private(cls.key_file(), answer["pem"])
            registered_settings.write(cls.env_file(), values)
            cls.code_file().unlink(missing_ok=True)
        except OSError as error:
            raise RegistrationNotSaved(f"{settings.DATA_DIR}: {error}") from error
        cls.apply(values, answer["pem"])

    @staticmethod
    def apply(values: dict[str, str], key: str) -> None:
        """Use the new credentials in this process, where the environment sets none.

        Args:
            values: The settings by name.
            key: The private key.
        """
        registered_settings.load_values(values, os.environ)
        settings.GITHUB_APP_ID = os.environ["GITHUB_APP_ID"]
        settings.GITHUB_APP_SLUG = os.environ["GITHUB_APP_SLUG"]
        settings.GITHUB_WEBHOOK_SECRET = os.environ["GITHUB_WEBHOOK_SECRET"]
        settings.GITHUB_APP_PRIVATE_KEY = key
        settings.SOCIALACCOUNT_PROVIDERS["github"]["APP"] = {
            "client_id": os.environ["GITHUB_CLIENT_ID"],
            "secret": os.environ["GITHUB_SECRET"],
        }

    @staticmethod
    def reload_workers(request) -> bool:
        """Let the other processes of gunicorn read the new settings.

        Args:
            request: The request; gunicorn names itself in ``SERVER_SOFTWARE``.

        Returns:
            True if gunicorn was asked to restart its workers gracefully.
        """
        if not request.META.get("SERVER_SOFTWARE", "").startswith("gunicorn"):
            return False
        os.kill(os.getppid(), signal.SIGHUP)
        return True
