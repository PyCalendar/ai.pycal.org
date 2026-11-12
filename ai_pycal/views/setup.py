"""The pages of administrators: install the GitHub App and add repositories."""

from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import validate_email
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
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
from ai_pycal.services.repository_sync import RepositorySync


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


def github_callback(request):
    """The callback of signing in with GitHub, which GitHub also uses after an installation.

    An app with *Request user authorization (OAuth) during installation* sends people to
    the callback after they installed it, with ``installation_id`` and ``setup_action``
    but without the ``state`` of a sign-in that the site started; allauth refuses that as
    a failed sign-in. Such a return goes to ``/setup/installed/`` (without the code), the
    page for installations; every other request is the callback of allauth.

    Args:
        request: The request.

    Returns:
        A redirect to ``/setup/installed/``, or the answer of allauth.
    """
    from allauth.socialaccount.providers.github.views import oauth2_callback

    if "state" not in request.GET and request.GET.get("installation_id"):
        query = urlencode(
            {
                key: request.GET[key]
                for key in ("installation_id", "setup_action")
                if request.GET.get(key)
            }
        )
        return redirect(f"{reverse('installed')}?{query}")
    return oauth2_callback(request)


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


def may_update(user, repository: Repository) -> bool:
    """Whether a person may read the configuration of a project again.

    Args:
        user: The user.
        repository: The project.

    Returns:
        True for staff and for administrators of the installation of the app.
    """
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_staff:
        return True
    installation = repository.installation
    return bool(installation and installation.admins.filter(pk=user.pk).exists())


@login_required
@require_POST
def update_project(request, owner: str, repo: str):
    """Read the configuration and the agreements of a project again, and check its pull requests.

    As a push to the default branch does; for administrators of the installation.

    Args:
        request: The request.
        owner: The owner of the repository.
        repo: The name of the repository.

    Returns:
        Back to the page of the project, with a message.
    """
    repository = repository_or_404(f"{owner}/{repo}")
    if not may_update(request.user, repository):
        raise PermissionDenied(repository.full_name)
    setup = RepositorySetup(repository)
    try:
        RepositorySync(repository, setup.api).sync()
    except AgreementError as error:
        messages.error(request, f"{error.title}: {error}")
    else:
        checked = setup.check_open_pulls()
        messages.success(
            request,
            _("The configuration was read again; %(count)d open pull requests were checked.")
            % {"count": checked},
        )
    return redirect(f"/project/{repository.full_name}/")


def older_address(request, owner: str, repo: str, number: int | None = None):
    """The older addresses of repositories, without ``repository/``, for links that use them.

    Only repositories that the site knows are redirected; any other address of two parts,
    such as ``/accounts/signup/``, is not found.

    Args:
        request: The request.
        owner: The owner of the repository.
        repo: The name of the repository.
        number: The number of a pull request, or None.

    Returns:
        A permanent redirect to ``/repository/...``.

    Raises:
        Http404: The site knows no such repository.
    """
    if not Repository.objects.filter(full_name__iexact=f"{owner}/{repo}").exists():
        raise Http404(f"{owner}/{repo}")
    kwargs = {"owner": owner, "repo": repo}
    if number is None:
        target = reverse("repository", kwargs=kwargs)
    else:
        target = reverse("pull_request", kwargs={**kwargs, "number": number})
    query = request.META.get("QUERY_STRING", "")
    return redirect(f"{target}?{query}" if query else target, permanent=True)


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
