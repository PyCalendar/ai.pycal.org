"""What a person has to do: agreements to sign, and problems of the projects they maintain."""

from django.db.models import Prefetch, Q

from ai_pycal.models import ProjectProblem, PullRequest, RequiredAgreement, Signature
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

    def to_sign(self) -> list[RequiredAgreement]:
        """The agreements to sign, each once, mandatory first.

        An agreement is to sign if an open pull request of the person needs it, or if the
        person signed an earlier version of it and a project now asks for a newer one. Such
        an agreement has ``signed_before``: the signature of the earlier version.

        Returns:
            The agreements of projects, with ``signed_before`` (a signature or None).
        """
        signatures = self.signatures()
        signed = {signature.version_id for signature in signatures}
        found: dict[int, RequiredAgreement] = {}
        for pull in self.open_pulls():
            for state in PullRequestCheck(pull).states():
                if state.required and state.agreement.version_id not in signed:
                    found.setdefault(state.agreement.version_id, state.agreement)
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
        for agreement in found.values():
            agreement.signed_before = latest.get((agreement.version.source, agreement.version.path))
        return sorted(found.values(), key=lambda a: (not a.mandatory, a.name.lower()))

    def problems(self) -> list[ProjectProblem]:
        """The active problems of the projects that the person watches or administers."""
        return list(
            ProjectProblem.objects.filter(
                Q(repository__watchers=self.user) | Q(repository__installation__admins=self.user),
                active=True,
            )
            .select_related("repository")
            .distinct()
        )

    def count(self) -> int:
        """The number of to-dos, for the menu."""
        return len(self.to_sign()) + len(self.problems())
