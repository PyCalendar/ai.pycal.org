"""The signing flow of a pull request: ``/project/<owner>/<repo>/pulls/<number>/sign/``.

The checks of a pull request link here. The author signs in, then signs the agreements of
the pull request one after the other, required ones first; optional ones can be skipped. The
flow shows only its steps and the progress: no links in the title bar, only About in the
footer, in a new tab. At the end, the author returns to the pull request on GitHub or to its
page on the site.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from ai_pycal.actions import Trigger
from ai_pycal.errors import AgreementNotShown, SigningError
from ai_pycal.middleware import error_page
from ai_pycal.services.agreement_text import AgreementText
from ai_pycal.services.identity import GitHubIdentity
from ai_pycal.services.pull_request_check import PullRequestCheck
from ai_pycal.services.signer import Signer

from .agreements import handle_pattern
from .policies import assert_author, pull_for

SKIPPED = "signing-flow-skipped"


def skipped(request, pull) -> set[int]:
    """The optional agreements that the person skipped in the flow of a pull request.

    Args:
        request: The request; the session keeps them.
        pull: The pull request.

    Returns:
        The ids of the versions.
    """
    return set(request.session.get(SKIPPED, {}).get(str(pull.pk), []))


def skip(request, pull, version_id: int) -> None:
    """Skip an optional agreement in the flow of a pull request.

    Args:
        request: The request.
        pull: The pull request.
        version_id: The version of the agreement.
    """
    found = request.session.get(SKIPPED, {})
    found[str(pull.pk)] = sorted(skipped(request, pull) | {version_id})
    request.session[SKIPPED] = found


@login_required
@Trigger.view("signed", "@{login} signs in the flow of #{number}")
def flow(request, owner: str, repo: str, number: int):
    """The signing flow of a pull request, one agreement at a time.

    Args:
        request: The request; POST with ``version``, ``shown``, ``accept``, ``handle`` and
            ``action`` (``sign`` or ``skip``).
        owner: The owner of the repository.
        repo: The name of the repository.
        number: The number of the pull request.

    Returns:
        The step, the end of the flow, or a redirect to the next step.
    """
    pull = pull_for(request, owner, repo, number)
    here = reverse("sign_pull", kwargs={"owner": owner, "repo": repo, "number": number})
    page = reverse("project_pull", kwargs={"owner": owner, "repo": repo, "number": number})
    identity = GitHubIdentity.of(request.user)
    context = {"pull": pull, "here": here, "page": page, "flow": True}
    if request.method == "POST":
        assert_author(request, pull)  # someone else's POST: NotPullRequestAuthor, 403
        if "version" not in request.POST:
            return error_page(request, AgreementNotShown("no agreement was shown"))
    if identity is None or identity.github_id != pull.author_github_id:
        return render(request, "ai_pycal/signing_flow.html", {**context, "not_author": True})
    check = PullRequestCheck(pull)
    if pull.repository.choices.exists() and check.choice() is None:
        return render(
            request,
            "ai_pycal/signing_flow.html",
            {**context, "choose": True, "choices": list(pull.repository.choices.all())},
        )
    states = check.states()
    ordered = [s for s in states if s.required] + [s for s in states if not s.required]
    passed = skipped(request, pull)
    # a skip hides only optional agreements: one that became required is asked again
    remaining = [
        s for s in ordered if not s.signed and (s.required or s.agreement.version_id not in passed)
    ]
    signer = Signer(request.user, identity)
    error = None
    if request.method == "POST":
        current = next(
            (s for s in remaining if str(s.agreement.version_id) == request.POST["version"]),
            None,
        )
        if current is None:  # signed meanwhile, or not of this pull request
            return redirect(here)
        if request.POST.get("action") == "skip":
            if not current.required:
                skip(request, pull, current.agreement.version_id)
            return redirect(here)
        try:
            signer.sign(
                current.agreement.version,
                accepted=request.POST.get("accept") == "yes",
                handle=request.POST.get("handle", ""),
                token=request.POST.get("shown", ""),
            )
        except SigningError as found:
            error = found
        else:
            return redirect(here)
    if not remaining:
        return render(
            request,
            "ai_pycal/signing_flow.html",
            {
                **context,
                "done": True,
                "skipped_count": sum(1 for s in ordered if not s.signed),
                "missing": any(s.required and not s.signed for s in ordered),
            },
        )
    current = remaining[0]
    version = current.agreement.version
    return render(
        request,
        "ai_pycal/signing_flow.html",
        {
            **context,
            "state": current,
            "position": ordered.index(current) + 1,
            "total": len(ordered),
            "more": len(remaining) > 1,
            "text": (text := AgreementText.of(version, request)),
            "html": text.html,
            "shown_token": signer.shown_token(version),
            "handle_pattern": handle_pattern(identity.login),
            "sign_error": error,
            "handle": request.POST.get("handle", "") if error else "",
        },
        status=error.status if error else 200,
    )
