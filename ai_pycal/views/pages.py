"""The pages about the site: start, about, health, the icon and the colors."""

from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.db import connection
from django.http import FileResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_POST

from ai_pycal import build_info
from ai_pycal.checks import FAVICON_TYPES
from ai_pycal.models import Repository, Signature
from ai_pycal.theme import COOKIE, Theme


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


def about(request):
    """The About page: the links of the site, the version, its commit and its build.

    Args:
        request: The request.

    Returns:
        The page.
    """
    return render(
        request,
        "ai_pycal/about.html",
        {"build": build_info.get(settings.SOURCE_URL), "time_zone": settings.TIME_ZONE},
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


@require_POST
def theme(request):
    """Remember the colors chosen with the switch in the footer, without JavaScript.

    The choice is kept for a year in the cookie ``theme``; ``auto`` removes it, so that the
    system decides again.

    Args:
        request: The request, with ``theme`` (``auto``, ``light`` or ``dark``) and ``next``.

    Returns:
        A redirect back to ``next`` on this site, or to the start page.
    """
    target = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        target = "/"
    response = HttpResponseRedirect(target)
    choice = Theme.choice(request.POST.get("theme"))
    if choice == "auto":
        response.delete_cookie(COOKIE, samesite="Lax")
    else:
        response.set_cookie(
            COOKIE, choice, max_age=365 * 24 * 3600, samesite="Lax", secure=request.is_secure()
        )
    return response
