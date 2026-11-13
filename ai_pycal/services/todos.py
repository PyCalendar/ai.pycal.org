"""What a person has to do: agreements to sign, and problems of the projects they maintain."""

from django.db.models import Prefetch, Q

from ai_pycal.errors import ConfigFileNotFound
from ai_pycal.models import (
    ProjectProblem,
    PullRequest,
    RequiredAgreement,
    Signature,
    TodoDismissal,
)
from ai_pycal.services.pull_request_check import PullRequestCheck
from ai_pycal.services.visibility import visible_projects


class Todos:
    """The to-dos of a signed-in person, for the page Todos and the count in the menu."""

    def __init__(self, user, identity):
        """The to-dos of a person.

        Args:
            user: The user of Django.
            identity: The GitHub identity of the user, or None.
        """
        self.user = user
        self.identity = identity

    def signatures(self) -> list[Signature]:
        """The signatures of the person, newest first.

        Returns:
            The signatures, each with ``agreement``: the agreement of a project that asks
            for this file, to name it for people; None if no visible project does.
        """
        if not self.identity:
            return []
        signatures = list(
            Signature.objects.filter(github_id=self.identity.github_id).select_related("version")
        )
        visible = visible_projects(self.user).filter(active=True)
        for signature in signatures:
            same_file = RequiredAgreement.objects.filter(
                version__source=signature.version.source,
                version__path=signature.version.path,
                repository__in=visible,
            ).select_related("repository")
            signature.agreement = (
                same_file.filter(version=signature.version).first() or same_file.first()
            )
        return signatures

    def open_pulls(self) -> list[PullRequest]:
        """The open pull requests of the person in active projects."""
        if not self.identity:
            return []
        return list(
            PullRequest.objects.filter(
                author_github_id=self.identity.github_id, open=True, repository__active=True
            )
            .select_related("repository")
            .prefetch_related(
                Prefetch(
                    "repository__required_agreements",
                    queryset=RequiredAgreement.objects.select_related("version"),
                )
            )
        )

    def all_pulls(self) -> list[PullRequest]:
        """All pull requests of the person in active projects, open ones first."""
        if not self.identity:
            return []
        return list(
            PullRequest.objects.filter(
                author_github_id=self.identity.github_id, repository__active=True
            )
            .select_related("repository")
            .order_by("-open", "-number")
        )

    def to_sign(self, dismissed: bool = False) -> list[RequiredAgreement]:
        """The agreements to sign, each once: required first, then optional ones.

        An agreement is to sign if a pull request of the person needs it, if it is an
        optional agreement of a project where the person has an open pull request, or if
        the person signed an earlier version and a project now asks for a newer one.

        Args:
            dismissed: Also the optional agreements that the person dismissed.

        Returns:
            The agreements of projects, with ``signed_before`` (the signature of an earlier
            version, or None), ``required_for_me`` (a pull request needs it, or it is
            mandatory; only the others can be dismissed) and ``dismissed``.
        """
        signatures = self.signatures()
        signed = {signature.version_id for signature in signatures}
        found: dict[int, RequiredAgreement] = {}
        required: set[int] = set()
        for pull in self.open_pulls():
            for state in PullRequestCheck(pull).states():
                if state.agreement.version_id in signed:
                    continue
                found.setdefault(state.agreement.version_id, state.agreement)
                if state.required:
                    required.add(state.agreement.version_id)
        latest: dict[tuple[str, str], Signature] = {}
        for signature in signatures:
            latest.setdefault((signature.version.source, signature.version.path), signature)
        if latest:
            condition = Q()
            for source, path in latest:
                condition |= Q(version__source=source, version__path=path)
            updated = (
                RequiredAgreement.objects.filter(
                    condition,
                    repository__active=True,
                    repository__in=visible_projects(self.user),
                )
                .exclude(version_id__in=signed)
                .select_related("version", "repository")
            )
            for agreement in updated:
                found.setdefault(agreement.version_id, agreement)
        hidden = set(
            TodoDismissal.objects.filter(user=self.user, version_id__in=found).values_list(
                "version_id", flat=True
            )
        )
        result = []
        for agreement in found.values():
            agreement.signed_before = latest.get((agreement.version.source, agreement.version.path))
            agreement.required_for_me = agreement.mandatory or agreement.version_id in required
            agreement.dismissed = not agreement.required_for_me and agreement.version_id in hidden
            if dismissed or not agreement.dismissed:
                result.append(agreement)
        return sorted(result, key=lambda a: (not a.required_for_me, a.name.lower()))

    def dismiss(self, version_id: int) -> bool:
        """Remove an optional agreement from the todos, until it changes.

        Args:
            version_id: The version of the agreement.

        Returns:
            True if it was dismissed; False if it is not an optional todo of the person.
        """
        for agreement in self.to_sign(dismissed=True):
            if agreement.version_id == version_id and not agreement.required_for_me:
                TodoDismissal.objects.get_or_create(user=self.user, version_id=version_id)
                return True
        return False

    def problems(self) -> list[ProjectProblem]:
        """The active problems of the projects that the person watches or administers.

        A missing configuration file of a repository that is not added is left out: the
        installation has it, but it does not use the site.
        """
        return list(
            ProjectProblem.objects.filter(
                Q(repository__watchers=self.user) | Q(repository__installation__admins=self.user),
                active=True,
            )
            .exclude(code=ConfigFileNotFound.__name__, repository__active=False)
            .select_related("repository")
            .distinct()
        )

    def count(self) -> int:
        """The number of to-dos, for the menu."""
        return len(self.to_sign()) + len(self.problems())
