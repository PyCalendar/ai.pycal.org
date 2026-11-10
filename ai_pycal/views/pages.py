"""The pages about the site: start, health and the icon."""

from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.db import connection
from django.http import FileResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import cache_control

from ai_pycal.checks import FAVICON_TYPES
from ai_pycal.models import Repository, Signature


def home(request):
    """The start page: what the site does, for contributors and for administrators.

    Args:
        request: The request.

    Returns:
        The page.
    """
    return render(
        request,
        "ai_pycal/home.html",
        {
            "repositories": Repository.objects.filter(active=True).count(),
            "signatures": Signature.objects.count(),
        },
    )


def health(request):
    """Whether the database answers: for the health check of the container.

    Args:
        request: The request.

    Returns:
        ``{"status": "ok"}``, or 503.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception as error:  # noqa: BLE001 - any failure is unhealthy
        return JsonResponse({"status": "error", "detail": str(error)}, status=503)
    return JsonResponse({"status": "ok"})


@cache_control(max_age=86400, public=True)
def favicon(request):
    """The icon of the site: ``FAVICON_FILE``, or the icon of pycal.

    Args:
        request: The request.

    Returns:
        The image.
    """
    path = Path(settings.FAVICON_FILE) if settings.FAVICON_FILE else None
    if not path or not path.is_file():
        path = Path(finders.find("img/favicon.png"))
    return FileResponse(
        path.open("rb"), content_type=FAVICON_TYPES.get(path.suffix.lower(), "image/png")
    )
