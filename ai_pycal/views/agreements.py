"""The pages of agreements: read, compare and sign them."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch, Q
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from ai_pycal.errors import AgreementNotFound, SigningError
from ai_pycal.middleware import error_page
from ai_pycal.models import AgreementVersion, PullRequest, RequiredAgreement, Signature
from ai_pycal.services.agreement_diff import AgreementDiff
from ai_pycal.services.identity import GitHubIdentity
from ai_pycal.services.pull_request_check import PullRequestCheck
from ai_pycal.services.rendering import render as render_agreement
from ai_pycal.services.signer import Signer
from ai_pycal.services.visibility import visible_projects


def version_or_404(pk: int, user=None) -> AgreementVersion:
    """The version of an agreement.

    Args:
        pk: Its number.
        user: The visitor, used to hide agreements of private projects.

    Returns:
        The version.

    Raises:
        AgreementNotFound: There is none with this number.
    """
    visible = visible_projects(user)
    version = (
        AgreementVersion.objects.filter(
            Q(projects__in=visible) | Q(required_by__repository__in=visible), pk=pk
        )
        .distinct()
        .first()
    )
    if version is None:
        raise AgreementNotFound(str(pk))
    return version


@login_required
def mine(request):
    """My agreements: what I signed and what my pull requests need.

    Args:
        request: The request.

    Returns:
        The page.
    """
    identity = GitHubIdentity.of(request.user)
    signatures = []
    pulls = []
    if identity:
        signatures = list(
            Signature.objects.filter(github_id=identity.github_id).select_related("version")
        )
        pulls = list(
            PullRequest.objects.filter(
                author_github_id=identity.github_id, open=True, repository__active=True
            )
            .select_related("repository")
            .prefetch_related(
                Prefetch(
                    "repository__required_agreements",
                    queryset=RequiredAgreement.objects.select_related("version"),
                )
            )
        )
    signed = {signature.version_id for signature in signatures}
    to_sign: dict[int, RequiredAgreement] = {}
    for pull in pulls:
        for state in PullRequestCheck(pull).states():
            if state.required and state.agreement.version_id not in signed:
                to_sign.setdefault(state.agreement.version_id, state.agreement)
    return render(
        request,
        "ai_pycal/mine.html",
        {"signatures": signatures, "pulls": pulls, "to_sign": list(to_sign.values())},
    )


def show(request, pk: int):
    """An agreement, with the form to sign it and what changed since I signed it.

    Args:
        request: The request.
        pk: The number of the version.

    Returns:
        The page.
    """
    version = version_or_404(pk, request.user)
    identity = GitHubIdentity.of(request.user)
    signature = previous = None
    token = ""
    if identity:
        signature = Signature.objects.filter(version=version, github_id=identity.github_id).first()
        previous = AgreementDiff.previous_signed(version, identity.github_id)
        token = Signer(request.user, identity).shown_token(version)
    names = (
        RequiredAgreement.objects.filter(
            version=version, repository__active=True, repository__in=visible_projects(request.user)
        )
        .select_related("repository")
        .order_by("repository__full_name")
    )
    return render(
        request,
        "ai_pycal/agreement.html",
        {
            "version": version,
            "required_by": names,
            "title": names[0].name if names else version.path,
            "html": render_agreement(version.text, version.path),
            "signature": signature,
            "previous": previous,
            "changes": AgreementDiff(previous, version).changes() if previous else [],
            "shown_token": token,
            "next": request.GET.get("next", ""),
        },
    )


@login_required
@require_POST
def sign(request, pk: int):
    """Sign an agreement with the form of its page.

    Args:
        request: The request.
        pk: The number of the version.

    Returns:
        Back to the pull request or the agreement; the page of the error if it fails.
    """
    version = version_or_404(pk, request.user)
    identity = GitHubIdentity.of(request.user)
    if identity is None:
        return redirect("account_login")
    try:
        _signature, created = Signer(request.user, identity).sign(
            version,
            accepted=request.POST.get("accept") == "yes",
            handle=request.POST.get("handle", ""),
            token=request.POST.get("shown", ""),
        )
    except SigningError as error:
        return error_page(request, error)
    if created:
        messages.success(request, _("You signed the agreement. Your pull requests are updated."))
    else:
        messages.info(request, _("You had already signed this agreement."))
    target = request.POST.get("next", "")
    if target.startswith("/") and url_has_allowed_host_and_scheme(
        target, {request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(target)
    return redirect("agreement", pk=version.pk)


def changes(request, pk: int, old: int):
    """What changed between two versions of an agreement.

    Args:
        request: The request.
        pk: The number of the new version.
        old: The number of the old version.

    Returns:
        The page.
    """
    version = version_or_404(pk, request.user)
    previous = version_or_404(old, request.user)
    return render(
        request,
        "ai_pycal/changes.html",
        {
            "version": version,
            "previous": previous,
            "changes": AgreementDiff(previous, version).changes(),
        },
    )


def pull_request(request, owner: str, repo: str, number: int):
    """The agreements of a pull request: the details of its checks.

    Args:
        request: The request.
        owner: The owner of the repository.
        repo: The name of the repository.
        number: The number of the pull request.

    Returns:
        The page.
    """
    from .policies import pull

    return pull(request, owner, repo, number)
