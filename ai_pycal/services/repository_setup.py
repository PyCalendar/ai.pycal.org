"""Add a repository: read its configuration and check its open pull requests."""

import logging

from django.db.models import Q

from ai_pycal.errors import AgreementError
from ai_pycal.github.app import GitHubApp
from ai_pycal.github.repository_api import RepositoryAPI
from ai_pycal.models import PullRequest, Repository

from .pull_request_check import PullRequestCheck
from .repository_sync import RepositorySync

log = logging.getLogger(__name__)


class RepositorySetup:
    """Make a repository active when its configuration can be read."""

    def __init__(self, repository: Repository, api: RepositoryAPI | None = None):
        """The setup of *repository*.

        Args:
            repository: The repository.
            api: The requests; those of the installation of the repository by default.
        """
        self.repository = repository
        self.api = api or RepositoryAPI(
            GitHubApp.for_installation(repository.installation.github_id)
        )

    def add(self) -> int:
        """Read the configuration, activate the repository and check its pull requests.

        Returns:
            How many pull requests were checked.

        Raises:
            ConfigFileError: The configuration can not be used; the repository is not
                activated.
        """
        RepositorySync(self.repository, self.api).sync()
        self.repository.active = True
        self.repository.save(update_fields=["active"])
        return self.check_open_pulls()

    def check_open_pulls(self) -> int:
        """Store and check the open pull requests of the repository.

        Errors of single pull requests are logged; they are checked on their next change.

        Returns:
            How many pull requests were checked.
        """
        open_numbers = []
        for data in self.api.open_pulls(self.repository.full_name):
            pull, _ = PullRequest.objects.update_or_create(
                repository=self.repository,
                number=data["number"],
                defaults={
                    "title": (data.get("title") or "")[:500],
                    "author_github_id": data["user"]["id"],
                    "author_login": data["user"]["login"],
                    "head_sha": data["head"]["sha"],
                    "open": True,
                },
            )
            open_numbers.append(pull.number)
            try:
                PullRequestCheck(pull, self.api).run()
            except AgreementError as error:
                log.warning("%s: %s %s", pull, error.code, error)
        for pull in self.repository.pull_requests.exclude(number__in=open_numbers).filter(
            Q(open=True) | Q(merged=False, state_checked=False)
        ):
            self.read_state(pull)
        return len(open_numbers)

    def read_state(self, pull: PullRequest) -> None:
        """Read whether a pull request that is not open any more was merged or closed.

        A pull request that closed while a webhook was lost, or before the site kept
        ``merged``, gets its state; it is read once.

        Args:
            pull: The pull request.
        """
        try:
            data = self.api.pull(self.repository.full_name, pull.number)
        except AgreementError as error:
            log.warning("%s: %s %s", pull, error.code, error)
            pull.open = False
            pull.save(update_fields=["open"])
            return
        pull.open = data.get("state") == "open"
        pull.merged = bool(data.get("merged"))
        pull.state_checked = not pull.open
        pull.save(update_fields=["open", "merged", "state_checked"])
