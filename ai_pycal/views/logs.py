"""The logs: what triggered the site and which actions followed, for each page.

The addresses mirror the pages they log: ``/logs/<owner>/`` for the projects of an owner,
``/logs/<owner>/<repo>/`` for a project, ``/logs/<owner>/<repo>/pulls/<number>/`` for a pull
request,
``/logs/contributor/<handle>/`` for a person, and ``/logs/all/`` for the administrators.
Each shows only the triggers and actions that concern it.
"""

from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Prefetch, Q

from ai_pycal.models import LogAction, LogTrigger
from ai_pycal.services import public_data as data
from ai_pycal.services.identity import GitHubIdentity
from ai_pycal.services.visibility import visible_projects

from .json_page import page as json_page
from .policies import contributor_id, project_for, pull_for

PER_PAGE = 50


def is_site_admin(user) -> bool:
    """Whether a person administers the site; see :meth:`GitHubIdentity.is_site_admin`.

    Args:
        user: The user.

    Returns:
        True for administrators of the site.
    """
    return GitHubIdentity.is_site_admin(user)


def log_page(request, triggers, actions: Q, context: dict):
    """The page of a log.

    Args:
        request: The request; ``page`` is the page, ``trigger`` a trigger to open.
        triggers: The triggers that concern the page.
        actions: The actions of the triggers that the page shows.
        context: The title of the page: ``crumbs`` and ``scope``.

    Returns:
        The page, newest first.
    """
    triggers = triggers.distinct().prefetch_related(
        Prefetch("actions", queryset=LogAction.objects.filter(actions), to_attr="shown")
    )
    page = Paginator(triggers, PER_PAGE).get_page(request.GET.get("page"))
    try:
        opened = int(request.GET.get("trigger", ""))
    except ValueError:
        opened = None
    shown = page
    return json_page(
        request,
        "ai_pycal/logs.html",
        {**context, "page": shown, "opened": opened, "site_admin": is_site_admin(request.user)},
        lambda: {
            "scope": context["scope"],
            **{
                key: value
                for key, value in (
                    ("owner", context.get("owner")),
                    ("handle", context.get("handle")),
                    ("project", data.project(context["project"]) if "project" in context else None),
                    ("pull_request", data.pull(context["pull"]) if "pull" in context else None),
                )
                if value
            },
            "page": shown.number,
            "pages": shown.paginator.num_pages,
            "per_page": PER_PAGE,
            "triggers": [data.trigger(found) for found in shown],
        },
    )


def all_logs(request):
    """The global log: every trigger and action, also those that are not public.

    Args:
        request: The request.

    Returns:
        The page.

    Raises:
        PermissionDenied: The visitor is not in ``SITE_ADMINS``.
    """
    if not is_site_admin(request.user):
        raise PermissionDenied("SITE_ADMINS")
    return log_page(request, LogTrigger.objects.all(), Q(), {"scope": "all"})


def owner_log(request, owner: str):
    """The combined log of the projects of an organization or person.

    Args:
        request: The request.
        owner: The GitHub login.

    Returns:
        The page.
    """
    projects = visible_projects(request.user).filter(
        active=True, full_name__istartswith=f"{owner}/"
    )
    concerns = Q(repository__in=projects, public=True)
    triggers = LogTrigger.objects.filter(public=True).filter(
        Q(repository__in=projects) | Q(actions__repository__in=projects, actions__public=True)
    )
    return log_page(request, triggers, concerns, {"scope": "owner", "owner": owner})


def project_log(request, owner: str, repo: str):
    """The log of a project.

    Args:
        request: The request.
        owner: The owner of the repository.
        repo: The name of the repository.

    Returns:
        The page.
    """
    repository = project_for(request, owner, repo)
    concerns = Q(repository=repository, public=True)
    triggers = LogTrigger.objects.filter(public=True).filter(
        Q(repository=repository) | Q(actions__repository=repository, actions__public=True)
    )
    return log_page(
        request,
        triggers,
        concerns,
        {"scope": "project", "project": repository, "owner": repository.owner},
    )


def pull_log(request, owner: str, repo: str, number: int):
    """The log of a pull request.

    Args:
        request: The request.
        owner: The owner of the repository.
        repo: The name of the repository.
        number: The number of the pull request.

    Returns:
        The page.
    """
    pull = pull_for(request, owner, repo, number)
    concerns = Q(pull=pull, public=True)
    triggers = LogTrigger.objects.filter(public=True).filter(
        Q(pull=pull) | Q(actions__pull=pull, actions__public=True)
    )
    return log_page(
        request,
        triggers,
        concerns,
        {
            "scope": "pull",
            "pull": pull,
            "project": pull.repository,
            "owner": pull.repository.owner,
        },
    )


def contributor_log(request, handle: str):
    """The log of a person: their signatures and what happened to their pull requests.

    Args:
        request: The request.
        handle: The GitHub handle.

    Returns:
        The page.
    """
    github_id = contributor_id(handle)
    visible = visible_projects(request.user)
    in_view = Q(repository__isnull=True) | Q(repository__in=visible)
    concerns = Q(contributor_github_id=github_id, public=True) & in_view
    triggers = (
        LogTrigger.objects.filter(public=True)
        .filter(in_view)
        .filter(
            Q(contributor_github_id=github_id)
            | Q(actions__contributor_github_id=github_id, actions__public=True)
        )
        if github_id
        else LogTrigger.objects.none()
    )
    return log_page(request, triggers, concerns, {"scope": "contributor", "handle": handle})
