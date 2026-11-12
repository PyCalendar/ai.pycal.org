"""Apply the agreements and frozen policy choice of a pull request."""

from dataclasses import dataclass

from django.conf import settings
from django.urls import reverse

from ai_pycal.errors import CannotWriteLabels, GitHubError, MissingPermissions
from ai_pycal.github.app import GitHubApp
from ai_pycal.github.repository_api import RepositoryAPI
from ai_pycal.models import ContributorPreference, PullRequest, RequiredAgreement, Signature

from .project_notices import ProjectNotices


@dataclass(frozen=True)
class AgreementState:
    """A current signature and whether this pull request requires it."""

    agreement: RequiredAgreement
    signed: bool
    required: bool = True


class PullRequestCheck:
    """Reconcile managed labels and checks with a contributor's PR choice."""

    def __init__(self, pull: PullRequest, api: RepositoryAPI | None = None):
        """Select a pull request and optionally inject its GitHub API.

        Args:
            pull: The pull request to check.
            api: The installation API, created lazily by default.
        """
        self.pull = pull
        self._api = api

    @property
    def api(self) -> RepositoryAPI:
        """The requests made with the project's installation token."""
        if self._api is None:
            self._api = RepositoryAPI(
                GitHubApp.for_installation(self.pull.repository.installation.github_id)
            )
        return self._api

    def choice(self):
        """Return the frozen choice, or a default for a PR not yet initialized."""
        pull = self.pull
        if pull.choice_initialized:
            return (
                pull.choice
                if pull.choice_id and pull.choice.repository_id == pull.repository_id
                else None
            )
        preference = (
            ContributorPreference.objects.filter(
                repository=pull.repository,
                github_id=pull.author_github_id,
                choice__repository=pull.repository,
            )
            .select_related("choice")
            .first()
        )
        return (
            preference.choice
            if preference
            else pull.repository.choices.filter(default=True).first()
        )

    def states(self) -> list[AgreementState]:
        """Read signatures and the selected bundle without contacting GitHub."""
        agreements = list(
            self.pull.repository.required_agreements.select_related("version").order_by(
                "-mandatory", "position"
            )
        )
        choice = self.choice()
        selected = set(choice.agreements.values_list("pk", flat=True)) if choice else set()
        signed = set(
            Signature.objects.filter(
                github_id=self.pull.author_github_id,
                version_id__in=[a.version_id for a in agreements],
            ).values_list("version_id", flat=True)
        )
        return [
            AgreementState(a, a.version_id in signed, a.mandatory or a.pk in selected)
            for a in agreements
        ]

    @staticmethod
    def labels(states: list[AgreementState]) -> tuple[set[str], set[str]]:
        """Return labels with satisfied dependencies and labels to remove.

        Args:
            states: The agreements and their signatures.

        Returns:
            The wanted and unwanted labels for agreements required on this PR.
        """
        wanted, unwanted = set(), set()
        for state in states:
            if state.required:
                (wanted if state.signed else unwanted).update(state.agreement.labels)
        return wanted - unwanted, unwanted

    def run(self) -> list[AgreementState]:
        """Freeze an initial default, update GitHub and persist the current result."""
        pull = self.pull
        if not pull.choice_initialized:
            pull.choice = self.choice()
            pull.choice_initialized = True
            pull.save(update_fields=["choice", "choice_initialized"])
        choice = self.choice()
        states = self.states()
        all_signed = all(s.signed for s in states if s.required)
        has_choices = pull.repository.choices.exists()
        all_signed = (
            all_signed
            and (not has_choices or choice is not None)
            and not pull.repository.error_code
        )
        # Never leave a previously successful result cached after a policy change.
        pull.all_signed = all_signed
        pull.save(update_fields=["all_signed", "updated"])
        add, blocked = self.labels(states)
        managed = set(pull.repository.managed_labels)
        managed.update(label for s in states for label in s.agreement.labels)
        for offered in pull.repository.choices.all():
            managed.update(offered.labels)
        if choice:
            add.update(choice.labels)
        add -= blocked
        name = pull.repository.full_name
        notice = ProjectNotices(pull.repository)
        try:
            present = set(self.api.labels(name, pull.number))
            self.api.add_labels(name, pull.number, sorted(add - present))
            for label in sorted((managed - add) & present):
                self.api.remove_label(name, pull.number, label)
        except (GitHubError, MissingPermissions) as error:
            if error.status not in (403, 404):
                raise
            failure = CannotWriteLabels(str(error))
            notice.record(failure)
            raise failure from error
        notice.resolve("CannotWriteLabels")
        owner, repo = name.split("/")
        details = settings.SITE_URL + reverse(
            "project_pull", kwargs={"owner": owner, "repo": repo, "number": pull.number}
        )
        checks = set()
        self.api.set_status(
            name,
            pull.head_sha,
            f"{settings.STATUS_CONTEXT}/configuration/setup",
            "error" if pull.repository.error_code else "success",
            f"Project setup needs attention: {pull.repository.error_code}"
            if pull.repository.error_code
            else "Project configuration is valid",
            details,
        )
        for state in states:
            agreement = state.agreement
            checks.add(agreement.key)
            if not state.required:
                status, text = "success", f"{agreement.name} is not required for this choice"
            elif state.signed:
                status, text = "success", f"@{pull.author_login} signed {agreement.name}"
            else:
                status, text = "pending", f"@{pull.author_login}: please sign {agreement.name}"
            self.api.set_status(
                name,
                pull.head_sha,
                f"{settings.STATUS_CONTEXT}/{agreement.key}",
                status,
                text,
                details,
            )
        if has_choices:
            checks.add("choices/selection")
            self.api.set_status(
                name,
                pull.head_sha,
                f"{settings.STATUS_CONTEXT}/choices/selection",
                "success" if all_signed else "pending",
                f"Choice: {choice.name}" if choice else "Please select a policy choice",
                details,
            )
        for obsolete in set(pull.repository.managed_checks) - checks:
            self.api.set_status(
                name,
                pull.head_sha,
                f"{settings.STATUS_CONTEXT}/{obsolete}",
                "success",
                "This check is no longer required by the project",
                details,
            )
        return states
