"""Project directories, public contributor records and machine-readable policy status."""

from allauth.socialaccount.models import SocialAccount
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Prefetch, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.html import escape
from django.views.decorators.http import require_POST

from ai_pycal.actions import Trigger
from ai_pycal.errors import (
    AgreementNotFound,
    ChoiceNotFound,
    NotPullRequestAuthor,
    PullRequestNotFound,
    RepositoryNotFound,
)
from ai_pycal.models import (
    AgreementVersion,
    ContributorPreference,
    PullRequest,
    RequiredAgreement,
    Signature,
)
from ai_pycal.services.agreement_diff import AgreementDiff
from ai_pycal.services.identity import GitHubIdentity
from ai_pycal.services.pull_request_check import PullRequestCheck
from ai_pycal.services.pull_state import PullState
from ai_pycal.services.rendering import render as markdown
from ai_pycal.services.signer import Signer
from ai_pycal.services.visibility import visible_projects

from .agreements import handle_pattern
from .setup import may_update


def project_for(request, owner: str, repo: str):
    """Find a visible project or raise its documented not-found error."""
    project = (
        visible_projects(request.user)
        .filter(full_name__iexact=f"{owner}/{repo}", active=True)
        .first()
    )
    if project is None:
        raise RepositoryNotFound(f"{owner}/{repo}")
    return project


def contributor_id(handle: str):
    """Resolve a public handle to its stable GitHub identifier using known records."""
    account = SocialAccount.objects.filter(
        provider="github", extra_data__login__iexact=handle
    ).first()
    if account:
        return int(account.uid)
    signature = Signature.objects.filter(login__iexact=handle).first()
    if signature:
        return signature.github_id
    return (
        PullRequest.objects.filter(author_login__iexact=handle)
        .values_list("author_github_id", flat=True)
        .first()
    )


def projects(request, owner: str = ""):
    """The directory of projects visible to this visitor, or those of one owner.

    Args:
        request: The request.
        owner: The GitHub login of an organization or person; "" for all.

    Returns:
        The page.
    """
    found = (
        visible_projects(request.user)
        .filter(active=True)
        .prefetch_related(
            Prefetch(
                "required_agreements",
                queryset=RequiredAgreement.objects.select_related("version"),
            )
        )
    )
    if owner:
        found = found.filter(full_name__istartswith=f"{owner}/")
    owners: dict[str, list] = {}
    for project in found.order_by("full_name"):
        owners.setdefault(project.owner, []).append(project)
    return render(
        request,
        "ai_pycal/projects.html",
        {
            "owners": sorted(owners.items(), key=lambda item: item[0].lower()),
            "owner": owner,
            "setup_url": reverse("setup"),
        },
    )


def signing_state(policy, github_id: int | None) -> str:
    """Whether a person signed the version of an agreement that a project asks for.

    Args:
        policy: The agreement of the project.
        github_id: The person; None for visitors.

    Returns:
        ``signed``, ``outdated`` (an earlier version is signed), ``unsigned``, or "" for
        visitors.
    """
    if github_id is None:
        return ""
    if Signature.objects.filter(version=policy.version, github_id=github_id).exists():
        return "signed"
    if AgreementDiff.previous_signed(policy.version, github_id):
        return "outdated"
    return "unsigned"


def project(request, owner: str, repo: str):
    """Show current policies, choices and the people who signed their exact versions.

    Each agreement has a badge, mandatory or optional, and for a signed-in person the
    state of their signature. Mandatory agreements that are unsigned and agreements whose
    signature is outdated need attention: the page lists them at the top.

    Args:
        request: The request.
        owner: The owner of the repository.
        repo: The name of the repository.

    Returns:
        The page.
    """
    repository = project_for(request, owner, repo)
    identity = GitHubIdentity.of(request.user)
    github_id = identity.github_id if identity else None
    policies = list(repository.required_agreements.select_related("version"))
    for policy in policies:
        policy.signers = policy.version.signatures.all()
        policy.description_html = markdown(policy.description, "description.md")
        policy.state = signing_state(policy, github_id)
        policy.attention = policy.state == "outdated" or (
            policy.state == "unsigned" and policy.mandatory
        )
    choices = list(repository.choices.all())
    for choice in choices:
        choice.description_html = markdown(choice.description, "description.md")
    return render(
        request,
        "ai_pycal/project.html",
        {
            "project": repository,
            "policies": policies,
            "attention": [policy for policy in policies if policy.attention],
            "can_update": may_update(request.user, repository),
            "show_all": request.GET.get("pulls") == "all",
            "pulls": PullState.annotate(
                repository.pull_requests.select_related("repository").order_by("-number")
                if request.GET.get("pulls") == "all"
                else repository.pull_requests.filter(open=True)
                .select_related("repository")
                .order_by("-number")
            ),
            "log_url": reverse("project_log", args=[repository.owner, repository.name]),
            "choices": choices,
        },
    )


def contributor(request, handle: str):
    """Show dated signatures, engaged projects and PR choices; hide other projects in details."""
    github_id = contributor_id(handle)
    visible = visible_projects(request.user).filter(active=True)
    signatures = (
        list(
            Signature.objects.filter(github_id=github_id, version__projects__in=visible)
            .select_related("version")
            .distinct()
        )
        if github_id
        else []
    )
    for signature in signatures:
        signature.projects = visible.filter(
            required_agreements__version=signature.version
        ).distinct()
        # the agreement of a project, to name it for people instead of its file
        signature.agreement = (
            RequiredAgreement.objects.filter(version=signature.version, repository__in=visible)
            .select_related("repository")
            .first()
        )
    engaged = (
        visible.filter(
            Q(pull_requests__author_github_id=github_id)
            | Q(required_agreements__version__signatures__github_id=github_id)
        ).distinct()
        if github_id
        else visible.none()
    )
    pulls = PullState.annotate(
        PullRequest.objects.filter(repository__in=visible, author_github_id=github_id)
        .select_related("repository", "choice")
        .order_by("-open", "-number")
        if github_id
        else PullRequest.objects.none()
    )
    identity = GitHubIdentity.of(request.user)
    preferences = (
        ContributorPreference.objects.filter(
            repository__in=visible, github_id=github_id
        ).select_related("repository", "choice")
        if github_id
        else []
    )
    return render(
        request,
        "ai_pycal/contributor.html",
        {
            "handle": handle,
            "signatures": signatures,
            "engaged": engaged,
            "others": visible.exclude(pk__in=engaged.values("pk")),
            "pulls": pulls,
            "preferences": preferences,
            "is_self": identity is not None and identity.github_id == github_id,
        },
    )


def history(request, owner: str, repo: str, agreement_path: str):
    """Show all visible commits currently or previously used from a repository path."""
    visible = visible_projects(request.user).filter(active=True)
    versions = AgreementVersion.objects.filter(
        source__iexact=f"{owner}/{repo}", path=agreement_path
    )
    if not versions.filter(projects__in=visible).exists():
        raise AgreementNotFound(f"{owner}/{repo}/{agreement_path}")
    rows = []
    for version in versions:
        # An older version is public only if it was used by a visible project or
        # the source is itself a visible project. Never disclose private-only text.
        if version.projects.filter(pk__in=visible.values("pk")).exists():
            rows.append(
                {
                    "version": version,
                    "projects": visible.filter(required_agreements__version=version).distinct(),
                }
            )
    return render(
        request,
        "ai_pycal/history.html",
        {
            "source": f"{owner}/{repo}",
            "path": agreement_path,
            "versions": rows,
            "agreement": RequiredAgreement.objects.filter(
                version__source__iexact=f"{owner}/{repo}",
                version__path=agreement_path,
                repository__in=visible,
            )
            .select_related("repository")
            .first(),
        },
    )


def pull_for(request, owner: str, repo: str, number: int):
    """Read a known pull request in a visible project."""
    repository = project_for(request, owner, repo)
    pull = (
        repository.pull_requests.select_related("repository__installation", "choice")
        .filter(number=number)
        .first()
    )
    if pull is None:
        raise PullRequestNotFound(f"{owner}/{repo}#{number}")
    return pull


def assert_author(request, pull):
    """Require the authenticated contributor to be the PR's author."""
    identity = GitHubIdentity.of(request.user)
    if identity is None or identity.github_id != pull.author_github_id:
        raise NotPullRequestAuthor()
    return identity


def my_pulls(request, repository, identity):
    """The pull requests of the visitor in a project, for the menu of the title.

    Args:
        request: The request; ``q`` filters by title or number.
        repository: The project.
        identity: The GitHub identity of the visitor, or None.

    Returns:
        The pull requests, the highest number first; none for visitors.
    """
    if identity is None:
        return []
    found = repository.pull_requests.filter(author_github_id=identity.github_id).order_by("-number")
    query = request.GET.get("q", "").strip()
    if query:
        number = query.lstrip("#")
        condition = Q(title__icontains=query)
        if number.isdigit():
            condition |= Q(number=int(number))
        found = found.filter(condition)
    return list(found[:50])


def pull(request, owner: str, repo: str, number: int):
    """A focused page with a public policy summary and author-only signing forms.

    Every agreement of the project is listed with its color: signed (green), unsigned
    and needed for this pull request (red), unsigned and optional (yellow). An outdated
    signature counts as unsigned.

    Args:
        request: The request.
        owner: The owner of the repository.
        repo: The name of the repository.
        number: The number of the pull request.

    Returns:
        The page.
    """
    item = pull_for(request, owner, repo, number)
    check = PullRequestCheck(item)
    identity = GitHubIdentity.of(request.user)
    is_author = identity is not None and identity.github_id == item.author_github_id
    states = check.states()
    rows = []
    for state in states:
        version = state.agreement.version
        rows.append(
            {
                "state": state,
                "html": markdown(version.text, version.path),
                "description": markdown(state.agreement.description, "description.md"),
                "token": Signer(request.user, identity).shown_token(version) if is_author else "",
            }
        )
    choices = list(item.repository.choices.all())
    for choice in choices:
        choice.description_html = markdown(choice.description, "description.md")
    here = reverse("project_pull", kwargs={"owner": owner, "repo": repo, "number": number})
    return render(
        request,
        "ai_pycal/pull_request.html",
        {
            "pull": item,
            "states": states,
            "rows": rows,
            "choices": choices,
            "choice": check.choice(),
            "is_author": is_author,
            "needs_signing": any(state.required and not state.signed for state in states),
            "focused": True,
            "here": here,
            "my_pulls": my_pulls(request, item.repository, identity),
            "query": request.GET.get("q", ""),
            "handle_pattern": handle_pattern(identity.login) if identity else "",
        },
    )


@login_required
@require_POST
@Trigger.view("choice", "@{login} chooses the policy of #{number}")
def choose(request, owner: str, repo: str, number: int):
    """Change only this PR's choice, optionally saving a default for future PRs."""
    item = pull_for(request, owner, repo, number)
    identity = assert_author(request, item)
    choice = item.repository.choices.filter(key=request.POST.get("choice", "")).first()
    if choice is None:
        raise ChoiceNotFound()
    with transaction.atomic():
        item.choice = choice
        item.choice_initialized = True
        item.save(update_fields=["choice", "choice_initialized"])
        if request.POST.get("default") == "yes":
            ContributorPreference.objects.update_or_create(
                repository=item.repository,
                github_id=identity.github_id,
                defaults={"choice": choice},
            )
    PullRequestCheck(item).run()
    messages.success(request, "Your PR choice is saved. Defaults apply only to future PRs.")
    return redirect("project_pull", owner=owner, repo=repo, number=number)


@login_required
@require_POST
@Trigger.view("choice", "@{login} sets a default policy for future pull requests")
def default_choice(request, owner: str, repo: str):
    """Set the contributor's project default without changing any existing PR."""
    repository = project_for(request, owner, repo)
    identity = GitHubIdentity.of(request.user)
    if identity is None:
        raise NotPullRequestAuthor()
    choice = repository.choices.filter(key=request.POST.get("choice", "")).first()
    if choice is None:
        raise ChoiceNotFound()
    ContributorPreference.objects.update_or_create(
        repository=repository, github_id=identity.github_id, defaults={"choice": choice}
    )
    messages.success(
        request,
        "Default saved for future PRs. Review existing PRs below to change them individually.",
    )
    return redirect("contributor", handle=identity.login)


@login_required
@require_POST
@Trigger.view("signed", "@{login} signs the agreements of #{number}")
def sign_pull(request, owner: str, repo: str, number: int):
    """Accept the displayed required agreements after validating every form token."""
    item = pull_for(request, owner, repo, number)
    identity = assert_author(request, item)
    signer = Signer(request.user, identity)
    unsigned = [s for s in PullRequestCheck(item).states() if not s.signed]
    # the required agreements must all be accepted; optional ones are signed if ticked
    states = [
        s
        for s in unsigned
        if s.required or request.POST.get(f"accept_{s.agreement.version_id}") == "yes"
    ]
    for state in states:
        signer.validate(
            state.agreement.version,
            request.POST.get(f"accept_{state.agreement.version_id}") == "yes",
            request.POST.get("handle", ""),
            request.POST.get(f"shown_{state.agreement.version_id}", ""),
        )
    for state in states:
        signer.sign(
            state.agreement.version,
            request.POST.get(f"accept_{state.agreement.version_id}") == "yes",
            request.POST.get("handle", ""),
            request.POST.get(f"shown_{state.agreement.version_id}", ""),
        )
    messages.success(request, "You signed the agreements.")
    return redirect("project_pull", owner=owner, repo=repo, number=number)


def policy_status(request, owner: str, repo: str, handle: str, policy: str, badge: bool = False):
    """Return a current-version signature as JSON or an escaped standalone SVG badge."""
    repository = project_for(request, owner, repo)
    agreement = repository.required_agreements.select_related("version").filter(key=policy).first()
    if agreement is None:
        raise AgreementNotFound(policy)
    github_id = contributor_id(handle)
    signature = (
        Signature.objects.filter(version=agreement.version, github_id=github_id).first()
        if github_id
        else None
    )
    if badge:
        state, color = ("signed", "#287a3d") if signature else ("not signed", "#8a6500")
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="24" role="img" '
            f'aria-label="{escape(policy)}: {state}">'
            f'<rect width="300" height="24" rx="4" fill="{color}"/>'
            '<text x="150" y="16" text-anchor="middle" fill="white" '
            f'font-family="sans-serif" font-size="12">{escape(policy)}: {state}</text></svg>'
        )
        response = HttpResponse(svg, content_type="image/svg+xml")
        response["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'unsafe-inline'; sandbox"
        )
    else:
        response = JsonResponse(
            {
                "project": repository.full_name,
                "contributor": handle,
                "policy": policy,
                "signed": signature is not None,
                "signed_at": signature.signed.isoformat() if signature else None,
                "mandatory": agreement.mandatory,
                "agreement": {
                    "repository": f"https://github.com/{agreement.version.source}",
                    "path": agreement.version.path,
                    "commit": agreement.version.commit,
                },
            }
        )
    response["Cache-Control"] = "no-store"
    return response
