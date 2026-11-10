"""The pages of administrators: install the GitHub App and add repositories."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from ai_pycal.errors import (
    AgreementError,
    ConfigFileError,
    InvalidNotificationEmail,
    RepositoryNotFound,
)
from ai_pycal.github import permissions
from ai_pycal.github.app import GitHubApp
from ai_pycal.middleware import error_page
from ai_pycal.models import Installation, Repository
from ai_pycal.services.admin_access import AdminAccess
from ai_pycal.services.permission_notice import PermissionNotice
from ai_pycal.services.repository_setup import RepositorySetup


@login_required
def setup(request):
    """The tutorial for administrators and their installations and repositories.

    Args:
        request: The request.

    Returns:
        The page.
    """
    installations = []
    error = None
    if GitHubApp.configured():
        try:
            access = AdminAccess(request.user)
            for found in access.installations():
                stored = Installation.objects.filter(github_id=found["id"]).first()
                installations.append(
                    {
                        "github": found,
                        "stored": stored,
                        "missing": permissions.describe(
                            permissions.missing(found.get("permissions") or {})
                        ),
                        "repositories": access.repositories(found["id"]),
                    }
                )
        except AgreementError as found_error:
            error = found_error
    return render(
        request,
        "ai_pycal/setup.html",
        {
            "install_url": GitHubApp.install_url(),
            "configured": GitHubApp.configured(),
            "installations": installations,
            "error": error,
            "required": sorted(permissions.REQUIRED.items()),
        },
    )


@login_required
def installed(request):
    """GitHub sends administrators here after they installed or changed the app.

    Args:
        request: The request, with ``installation_id``.

    Returns:
        To the page Setup.
    """
    try:
        installation_id = int(request.GET.get("installation_id", ""))
    except ValueError:
        return redirect("setup")
    installation = AdminAccess(request.user).installation(installation_id)
    PermissionNotice(installation).send_if_needed()
    messages.success(request, _("The GitHub App is installed on %s.") % installation)
    return redirect("setup")


@login_required
@require_POST
def add_repository(request, installation_id: int, repository_id: int):
    """Add a repository: read its configuration file and check its pull requests.

    Args:
        request: The request.
        installation_id: The id of the installation on GitHub.
        repository_id: The id of the repository on GitHub.

    Returns:
        To the page Setup, or the page of the error.
    """
    repository = AdminAccess(request.user).repository(installation_id, repository_id)
    try:
        checked = RepositorySetup(repository).add()
    except ConfigFileError as error:
        return error_page(request, error)
    messages.success(
        request,
        _("%(repository)s was added; %(count)d open pull requests were checked.")
        % {"repository": repository, "count": checked},
    )
    return redirect("setup")


@login_required
@require_POST
def remove_repository(request, installation_id: int, repository_id: int):
    """Stop checking the pull requests of a repository; the signatures stay.

    Args:
        request: The request.
        installation_id: The id of the installation on GitHub.
        repository_id: The id of the repository on GitHub.

    Returns:
        To the page Setup.
    """
    repository = AdminAccess(request.user).repository(installation_id, repository_id)
    repository.active = False
    repository.save(update_fields=["active"])
    messages.info(request, _("%s is no longer checked.") % repository)
    return redirect("setup")


@login_required
@require_POST
def notify_email(request, installation_id: int):
    """Set the address that is told when the app needs new permissions.

    Args:
        request: The request, with ``email``.
        installation_id: The id of the installation on GitHub.

    Returns:
        To the page Setup, or the page of the error.
    """
    email = request.POST.get("email", "").strip()
    if email:
        try:
            validate_email(email)
        except ValidationError:
            return error_page(request, InvalidNotificationEmail(email))
    installation = AdminAccess(request.user).installation(installation_id)
    installation.notify_email = email
    installation.save(update_fields=["notify_email", "updated"])
    messages.success(request, _("The email address was saved."))
    return redirect("setup")


def repository_or_404(full_name: str) -> Repository:
    """A repository the site knows.

    Args:
        full_name: ``owner/name``.

    Returns:
        The repository.

    Raises:
        RepositoryNotFound: The site does not know it.
    """
    repository = Repository.objects.filter(full_name__iexact=full_name).first()
    if repository is None:
        raise RepositoryNotFound(full_name)
    return repository


def repository(request, owner: str, repo: str):
    """The agreements a repository asks for, and the last error of its configuration.

    Args:
        request: The request.
        owner: The owner of the repository.
        repo: The name of the repository.

    Returns:
        The page.
    """
    from .policies import project

    return project(request, owner, repo)
