"""The pages of administrators: install the GitHub App and add repositories."""

import logging
from datetime import timedelta
from math import ceil
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import validate_email
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from ai_pycal.actions import Trigger
from ai_pycal.errors import (
    AgreementError,
    ConfigFileError,
    InvalidNotificationEmail,
    RepositoryNotFound,
)
from ai_pycal.github import permissions
from ai_pycal.github.app import GitHubApp
from ai_pycal.middleware import error_page
from ai_pycal.models import Installation, LogTrigger, Repository
from ai_pycal.services.admin_access import AdminAccess
from ai_pycal.services.identity import GitHubIdentity
from ai_pycal.services.permission_notice import PermissionNotice
from ai_pycal.services.repository_setup import RepositorySetup
from ai_pycal.services.repository_sync import RepositorySync

log = logging.getLogger(__name__)


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
            "app_events": app_events(request.user),
            "oauth_missing": GitHubApp.configured()
            and not settings.SIGN_IN_WITH_OAUTH_APP
            and GitHubIdentity.is_site_admin(request.user),
        },
    )


def app_events(user) -> dict | None:
    """The events that the app misses, for the administrators of the site.

    Args:
        user: The visitor.

    Returns:
        ``missing`` (the events) and ``url`` (the settings of the app on GitHub); None
        for other people, without an app, or if the app has all events.
    """
    if not GitHubApp.configured() or not GitHubIdentity.is_site_admin(user):
        return None
    try:
        app = GitHubApp.describe()
    except AgreementError as error:
        log.warning("the events of the app could not be read: %s", error.code)
        return None
    missing = permissions.missing_events(app.get("events") or [])
    return {"missing": missing, "url": GitHubApp.settings_url(app)} if missing else None


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
@Trigger.view("setup", "Repository added by @{login}")
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
@Trigger.view("setup", "Repository removed by @{login}")
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
@Trigger.view("setup", "Email of the installation changed by @{login}", public=False)
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


UPDATE_EVERY = timedelta(minutes=5)  # one manual update per person and project


def update_wait(user, repository: Repository) -> int:
    """How long a person waits before updating a project again by hand.

    The updates are the triggers ``update`` of the log; the one that is running is not
    counted.

    Args:
        user: The person.
        repository: The project.

    Returns:
        The minutes to wait, rounded up; 0 if the person may update now.
    """
    login = GitHubIdentity.of(user).login if GitHubIdentity.of(user) else user.username
    since = timezone.now() - UPDATE_EVERY
    last = (
        LogTrigger.objects.filter(
            kind="update", repository=repository, actor_login=login, created__gte=since
        )
        .exclude(pk=Trigger.current().pk)
        .order_by("-created")
        .first()
    )
    if last is None:
        return 0
    return max(1, ceil((last.created + UPDATE_EVERY - timezone.now()).total_seconds() / 60))


@login_required
@require_POST
@Trigger.view("update", "Repository configuration updated by @{login}")
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
    wait = update_wait(request.user, repository)
    if wait:
        messages.info(
            request,
            _("You updated this project recently. You can update it again in %(minutes)d minutes.")
            % {"minutes": wait},
        )
        return redirect(f"/project/{repository.full_name}/")
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
    """The older addresses of projects, ``/repository/...`` and without a prefix.

    Only repositories that the site knows are redirected; any other address of two parts,
    such as ``/accounts/signup/``, is not found.

    Args:
        request: The request.
        owner: The owner of the repository.
        repo: The name of the repository.
        number: The number of a pull request, or None.

    Returns:
        A permanent redirect to the page of the project or of the pull request.

    Raises:
        Http404: The site knows no such repository.
    """
    if not Repository.objects.filter(full_name__iexact=f"{owner}/{repo}").exists():
        raise Http404(f"{owner}/{repo}")
    kwargs = {"owner": owner, "repo": repo}
    if number is None:
        target = reverse("project", kwargs=kwargs)
    else:
        target = reverse("project_pull", kwargs={**kwargs, "number": number})
    query = request.META.get("QUERY_STRING", "")
    return redirect(f"{target}?{query}" if query else target, permanent=True)
