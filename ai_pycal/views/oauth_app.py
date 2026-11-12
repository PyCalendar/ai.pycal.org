"""The OAuth app that signs people in, entered on the site by its administrators.

People sign in with an OAuth app without scopes, so GitHub asks them no permission to act on
their behalf. GitHub has no manifest for OAuth apps: the administrators of the site create one
on GitHub and enter its client ID and secret here; they are kept in ``DATA_DIR/.env``, and
settings of the environment take precedence.
"""

import os
import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render

from ai_pycal import registered_settings
from ai_pycal.actions import Trigger
from ai_pycal.services.app_registration import AppRegistration
from ai_pycal.services.identity import GitHubIdentity

CLIENT_ID = re.compile(r"[A-Za-z0-9._-]{8,100}")
SECRET = re.compile(r"[A-Za-z0-9._-]{20,200}")


@login_required
def oauth_app(request):
    """Enter the OAuth app that signs people in: for the administrators of the site.

    Args:
        request: The request; POST with ``client_id`` and ``secret``.

    Returns:
        The page, or back to Setup after saving.

    Raises:
        PermissionDenied: The person is not in ``SITE_ADMINS``.
    """
    if not GitHubIdentity.is_site_admin(request.user):
        raise PermissionDenied("SITE_ADMINS")
    from_environment = bool(os.environ.get("GITHUB_OAUTH_CLIENT_ID")) and not (
        registered_settings.read(AppRegistration.env_file()).get("GITHUB_OAUTH_CLIENT_ID")
    )
    context = {
        "configured": settings.SIGN_IN_WITH_OAUTH_APP,
        "from_environment": from_environment,
        "callback_url": f"{settings.SITE_URL}/accounts/github/login/callback/",
        "site_url": settings.SITE_URL,
    }
    if request.method == "POST" and not from_environment:
        client_id = request.POST.get("client_id", "").strip()
        secret = request.POST.get("secret", "").strip()
        if not CLIENT_ID.fullmatch(client_id) or not SECRET.fullmatch(secret):
            context["error"] = True
            return render(request, "ai_pycal/oauth_app.html", context, status=400)
        with Trigger.start(
            "setup",
            "OAuth app for signing in entered",
            actor_login=request.user.username,
            public=False,
        ):
            registered_settings.write(
                AppRegistration.env_file(),
                {"GITHUB_OAUTH_CLIENT_ID": client_id, "GITHUB_OAUTH_SECRET": secret},
            )
        os.environ["GITHUB_OAUTH_CLIENT_ID"] = client_id
        os.environ["GITHUB_OAUTH_SECRET"] = secret
        settings.SIGN_IN_WITH_OAUTH_APP = True
        settings.SOCIALACCOUNT_PROVIDERS["github"]["APP"] = {
            "client_id": client_id,
            "secret": secret,
        }
        AppRegistration.reload_workers(request)
        messages.success(
            request, "People now sign in with the OAuth app; GitHub only tells who they are."
        )
        return redirect("setup")
    return render(request, "ai_pycal/oauth_app.html", context)
