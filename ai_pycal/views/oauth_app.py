"""The OAuth app that signs people in, entered on the site by its administrators.

People sign in with an OAuth app that reads who they are and their email addresses, so GitHub
asks them no permission to act on their behalf. GitHub has no manifest for OAuth apps: the
people who run the site create one on GitHub and enter its client ID and secret here; they are
kept in ``DATA_DIR/.env``, and settings of the environment take precedence.
"""

import os
import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

from ai_pycal import registered_settings
from ai_pycal.actions import Trigger
from ai_pycal.services.app_registration import AppRegistration
from ai_pycal.services.identity import GitHubIdentity

CLIENT_ID = re.compile(r"[A-Za-z0-9._-]{8,100}")
SECRET = re.compile(r"[A-Za-z0-9._-]{20,200}")


def may_enter(request) -> bool:
    """Whether this visitor may enter the OAuth app without the setup code.

    Args:
        request: The request.

    Returns:
        True for the administrators of the site (``SITE_ADMINS``).
    """
    return GitHubIdentity.is_site_admin(request.user)


def oauth_app(request):
    """Enter the OAuth app that signs people in.

    Until the site has one, nobody can sign in: the people who run the site enter it with
    the setup code of the log. Afterwards only the administrators of the site
    (``SITE_ADMINS``) change it.

    Args:
        request: The request; POST with ``client_id``, ``secret`` and ``setup_code``.

    Returns:
        The page, or back to Setup or the sign-in after saving.

    Raises:
        PermissionDenied: The site has an OAuth app and the person is not in ``SITE_ADMINS``.
    """
    admin = may_enter(request)
    if settings.SIGN_IN_WITH_OAUTH_APP and not admin:
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        raise PermissionDenied("SITE_ADMINS")
    from_environment = bool(os.environ.get("GITHUB_OAUTH_CLIENT_ID")) and not (
        registered_settings.read(AppRegistration.env_file()).get("GITHUB_OAUTH_CLIENT_ID")
    )
    context = {
        "configured": settings.SIGN_IN_WITH_OAUTH_APP,
        "from_environment": from_environment,
        "needs_code": not admin and AppRegistration.needs_setup_code(),
        "callback_url": f"{settings.SITE_URL}/accounts/github/login/callback/",
        "site_url": settings.SITE_URL,
    }
    if request.method == "POST" and not from_environment:
        client_id = request.POST.get("client_id", "").strip()
        secret = request.POST.get("secret", "").strip()
        if context["needs_code"] and not AppRegistration.code_matches(
            request.POST.get("setup_code", "")
        ):
            context["code_error"] = True
            return render(request, "ai_pycal/oauth_app.html", context, status=403)
        if not CLIENT_ID.fullmatch(client_id) or not SECRET.fullmatch(secret):
            context["error"] = True
            return render(request, "ai_pycal/oauth_app.html", context, status=400)
        with Trigger.start(
            "setup",
            "OAuth app for signing in entered",
            actor_login=request.user.username if admin else "",
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
            request, _("People now sign in with the OAuth app; GitHub only tells who they are.")
        )
        return redirect("setup" if admin else "account_login")
    return render(request, "ai_pycal/oauth_app.html", context)
