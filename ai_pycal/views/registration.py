"""Register the GitHub App of the site on the site: ``/setup/github-app/``.

Without JavaScript: the first form sends the name, the organization and the setup code to the
site, which answers with a form that sends the manifest to GitHub. GitHub returns to
``/setup/github-app/registered/``, where the site exchanges the code for the credentials.
"""

import json
import logging

from django.conf import settings
from django.shortcuts import render

from ai_pycal.actions import Trigger
from ai_pycal.errors import AgreementError, RegistrationError
from ai_pycal.middleware import error_page
from ai_pycal.services.app_registration import AppRegistration

log = logging.getLogger(__name__)


def register_app(request):
    """The page *Register GitHub App*: the form, or the app the site has.

    Args:
        request: The request; POST with ``name``, ``organization`` and ``setup_code``.

    Returns:
        The page; after a POST the form that sends the manifest to GitHub.
    """
    context = {
        "source": AppRegistration.source(),
        "slug": settings.GITHUB_APP_SLUG,
        "site_url": settings.SITE_URL,
        "local": AppRegistration.is_local(settings.SITE_URL),
        "needs_code": AppRegistration.needs_setup_code(),
        "name": request.POST.get("name", settings.SITE_NAME[:34]),
        "organization": request.POST.get("organization", ""),
    }
    if request.method == "POST":
        try:
            started = AppRegistration.start(
                request.session,
                request.POST.get("name", ""),
                request.POST.get("organization", ""),
                request.POST.get("setup_code", ""),
            )
        except RegistrationError as error:
            context["error"] = error
            return render(request, "ai_pycal/register_app.html", context, status=error.status)
        context.update(
            started=started,
            manifest_json=json.dumps(started["manifest"]),
            manifest_preview=json.dumps(started["manifest"], indent=2),
        )
    return render(request, "ai_pycal/register_app.html", context)


def app_registered(request):
    """GitHub returns here with ``code`` and ``state`` after it created the app.

    Args:
        request: The request.

    Returns:
        The page of the new app, or the page of the error with details to copy.
    """
    try:
        with Trigger.start("registration", "GitHub App registered on the site", public=False):
            app = AppRegistration.finish(
                request.session, request.GET.get("code", ""), request.GET.get("state", "")
            )
    except AgreementError as error:
        log.warning("registration of the GitHub App: %s %s", error.code, error)
        return error_page(request, error)
    log.info("registered the GitHub App %s (%s)", app.get("slug"), app.get("id"))
    reloaded = AppRegistration.reload_workers(request)
    return render(
        request,
        "ai_pycal/app_registered.html",
        {
            "app": app,
            "install_url": f"{app.get('html_url')}/installations/new",
            "local": AppRegistration.is_local(settings.SITE_URL),
            "reloaded": reloaded,
            "env_file": AppRegistration.env_file(),
            "key_file": AppRegistration.key_file(),
        },
    )
