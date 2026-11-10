"""The system checks of the settings: ``manage.py check`` and every start."""

from pathlib import Path

from django.conf import settings
from django.core.checks import Error, Warning, register

from .errors import FaviconNotFound, UnsupportedFavicon

FAVICON_TYPES = {".png": "image/png", ".ico": "image/x-icon", ".svg": "image/svg+xml"}


@register()
def check_favicon(app_configs=None, **kwargs) -> list:
    """``FAVICON_FILE`` is a PNG, ICO or SVG file that exists.

    Args:
        app_configs: The apps to check.
        **kwargs: More of Django.

    Returns:
        The errors.
    """
    path = settings.FAVICON_FILE
    if not path:
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
                hint="docs/how-to/github-app.rst",
                id="ai_pycal.W001",
            )
        ]
    return []
