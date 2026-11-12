"""Private account settings, verified email and project notifications."""

from allauth.account.models import EmailAddress
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from ai_pycal.errors import AgreementError
from ai_pycal.models import Profile
from ai_pycal.services.admin_access import AdminAccess


@login_required
@require_http_methods(["GET", "POST"])
def profile(request):
    """Manage email preferences and discover projects the person can write to.

    Args:
        request: The authenticated profile request.

    Returns:
        The private profile or a redirect after saving its preferences.
    """
    preferences, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        preferences.email_notifications = request.POST.get("email_notifications") == "yes"
        preferences.save(update_fields=["email_notifications"])
        messages.success(request, "Email preferences saved.")
        return redirect("profile")
    try:
        access = AdminAccess(request.user)
        for installation in access.installations():
            access.repositories(installation["id"])
    except AgreementError as error:
        messages.warning(request, f"{error.title}: {error}")
    return render(
        request,
        "ai_pycal/profile.html",
        {
            "preferences": preferences,
            "primary": EmailAddress.objects.filter(user=request.user, primary=True).first(),
            "projects": request.user.watched_projects.all(),
        },
    )
