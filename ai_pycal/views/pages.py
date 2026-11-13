"""The pages about the site: start, about, health, the icon and the colors."""

from dataclasses import asdict
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.db import connection
from django.http import FileResponse, Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_POST

from ai_pycal import build_info, licenses
from ai_pycal.checks import FAVICON_TYPES, is_url
from ai_pycal.models import Signature
from ai_pycal.services.public_data import links
from ai_pycal.services.visibility import visible_projects
from ai_pycal.theme import COOKIE, Theme

from .json_page import page


def home(request):
    """The start page: what the site does, for contributors and for administrators.

    Args:
        request: The request.

    Returns:
        The page.
    """
    context = {
        # what the visitor can see: private projects only for their people
        "repositories": visible_projects(request.user).filter(active=True).count(),
        "signatures": Signature.objects.count(),
    }
    return page(
        request,
        "ai_pycal/home.html",
        context,
        lambda: {
            "site": settings.SITE_NAME,
            "projects": context["repositories"],
            "signatures": context["signatures"],
            **links("/"),
            "pages": {"projects": links(reverse("projects")), "about": links(reverse("about"))},
        },
    )


def about(request):
    """The About page: the links of the site, the version, its commit and its build.

    Args:
        request: The request.

    Returns:
        The page.
    """
    build = build_info.get(settings.SOURCE_URL)
    return page(
        request,
        "ai_pycal/about.html",
        {"build": build},
        lambda: {
            "site": settings.SITE_NAME,
            "source": settings.SOURCE_URL,
            "documentation": settings.DOCS_URL,
            "build": {key: build[key] for key in (*build_info.FIELDS, "commit_url", "code_url")},
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
    """The icon of the site: ``FAVICON`` (an address or a file), or the icon of pycal.

    Args:
        request: The request.

    Returns:
        The image, or a redirect to the address of the icon.
    """
    if is_url(settings.FAVICON):
        return HttpResponseRedirect(settings.FAVICON)
    path = Path(settings.FAVICON) if settings.FAVICON else None
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


def licenses_page(request):
    """The licenses of the site: of the project, of code from other projects, of packages.

    Args:
        request: The request.

    Returns:
        The page.
    """
    context = {
        "project_license": licenses.PROJECT_LICENSE,
        "license_names": licenses.license_names(),
        "reused": licenses.reused(),
        "packages": licenses.packages(),
    }
    return page(
        request,
        "ai_pycal/licenses.html",
        context,
        lambda: {
            "license": context["project_license"],
            "licenses": [
                {"name": name, "text": reverse("license_text", args=[name])}
                for name in context["license_names"]
            ],
            "reused": [asdict(package) for package in context["reused"]],
            "packages": [asdict(package) for package in context["packages"]],
        },
    )


def license_text(request, name: str):
    """The text of a license of ``LICENSES/``, as plain text.

    Args:
        request: The request.
        name: The SPDX identifier, such as ``MIT``.

    Returns:
        The text.

    Raises:
        Http404: The project has no such license.
    """
    path = licenses.license_file(name)
    if path is None:
        raise Http404(name)
    return HttpResponse(path.read_text(), content_type="text/plain; charset=utf-8")


def package_license(request, name: str):
    """The text of the license of an installed Python package, as plain text.

    Args:
        request: The request.
        name: The name of the package.

    Returns:
        The text.

    Raises:
        Http404: The package is not installed or ships no license file.
    """
    text = licenses.package_license_text(name)
    if text is None:
        raise Http404(name)
    return HttpResponse(text, content_type="text/plain; charset=utf-8")
