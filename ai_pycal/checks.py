"""The system checks of the settings: ``manage.py check`` and every start."""

from pathlib import Path

from django.conf import settings
from django.core.checks import Error, Warning, register

from .errors import FaviconNotFound, UnsupportedFavicon

FAVICON_TYPES = {".png": "image/png", ".ico": "image/x-icon", ".svg": "image/svg+xml"}


def is_url(value: str) -> bool:
    """Whether the icon is an address on the web, not a file.

    Args:
        value: The value of ``FAVICON``.

    Returns:
        True for ``https://`` and ``http://``.

    Examples:
        >>> is_url("https://pycal.org/favicon.png"), is_url("/app/data/favicon.png")
        (True, False)
    """
    return value.startswith(("https://", "http://"))


@register()
def check_favicon(app_configs=None, **kwargs) -> list:
    """``FAVICON`` is an address, or a PNG, ICO or SVG file that exists.

    Args:
        app_configs: The apps to check.
        **kwargs: More of Django.

    Returns:
        The errors.
    """
    path = settings.FAVICON
    if not path or is_url(path):
        return []
    if Path(path).suffix.lower() not in FAVICON_TYPES:
        return [
            Error(
                UnsupportedFavicon.title,
                hint=path,
                id="ai_pycal.E002",
                obj=UnsupportedFavicon.docs_url(),
            )
        ]
    if not Path(path).is_file():
        return [
            Error(
                FaviconNotFound.title, hint=path, id="ai_pycal.E001", obj=FaviconNotFound.docs_url()
            )
        ]
    return []


@register()
def check_github_app(app_configs=None, **kwargs) -> list:
    """The GitHub App is configured; without it nobody can sign in.

    Args:
        app_configs: The apps to check.
        **kwargs: More of Django.

    Returns:
        The warnings.
    """
    missing = [
        name
        for name in (
            "GITHUB_APP_ID",
            "GITHUB_APP_SLUG",
            "GITHUB_APP_PRIVATE_KEY",
            "GITHUB_WEBHOOK_SECRET",
        )
        if not getattr(settings, name)
    ]
    if not settings.SOCIALACCOUNT_PROVIDERS["github"].get("APP"):
        missing.append("GITHUB_CLIENT_ID")
    if missing:
        return [
            Warning(
                "The GitHub App is not configured: " + ", ".join(missing),
                hint=f"Register it on {settings.SITE_URL}/setup/github-app/ "
                "(docs/how-to/github-app-site.rst)",
                id="ai_pycal.W001",
            )
        ]
    return []
