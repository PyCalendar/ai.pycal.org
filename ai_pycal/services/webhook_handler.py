"""Handle the webhooks of the GitHub App."""

import logging

from django.db import transaction

from ai_pycal.config import CONFIG_PATH
from ai_pycal.errors import AgreementError, WebhookPayloadInvalid
from ai_pycal.models import Installation, PullRequest, Repository

from .permission_notice import PermissionNotice
from .pull_request_check import PullRequestCheck
from .repository_sync import RepositorySync

log = logging.getLogger(__name__)
PULL_ACTIONS = {"opened", "reopened", "synchronize", "edited", "ready_for_review"}


class WebhookHandler:
    """Do what a webhook of GitHub asks for."""

    def __init__(self, event: str, payload: dict):
        """The handler of one webhook.

        Args:
            event: The header ``X-GitHub-Event``.
            payload: The JSON of the webhook.

        Raises:
            WebhookPayloadInvalid: The JSON is no mapping.
        """
        if not isinstance(payload, dict):
            raise WebhookPayloadInvalid(type(payload).__name__)
        self.event = event
        self.payload = payload

    def handle(self) -> str:
        """Handle the webhook.

        Returns:
            What was done, for the recent deliveries of the app.
        """
        method = getattr(self, f"on_{self.event}", None)
        if method is None:
            return f"ignored {self.event}"
        try:
            return method()
        except KeyError as error:
            raise WebhookPayloadInvalid(f"{self.event}: missing {error}") from error

    def on_ping(self) -> str:
        """GitHub checks the webhook.

        Returns:
            What was done.
        """
        return "pong"

    @staticmethod
    def store_installation(data: dict) -> Installation:
        """Store an installation as GitHub describes it.

        Args:
            data: The installation of a payload or of the API.

        Returns:
            The installation.
        """
        account = data.get("account") or {}
        installation, _ = Installation.objects.update_or_create(
            github_id=data["id"],
            defaults={
                "account_login": account.get("login", ""),
                "account_type": account.get("type", "User"),
                "permissions": data.get("permissions") or {},
                "suspended": bool(data.get("suspended_at")),
                "removed": False,
            },
        )
        return installation

    def on_installation(self) -> str:
        """The app was installed, removed, suspended or got new permissions.

        Returns:
            What was done.
        """
        action = self.payload.get("action", "")
        if action == "deleted":
            Installation.objects.filter(github_id=self.payload["installation"]["id"]).update(
                removed=True
            )
            Repository.objects.filter(
                installation__github_id=self.payload["installation"]["id"]
            ).update(active=False)
            return "removed"
        installation = self.store_installation(self.payload["installation"])
        PermissionNotice(installation).send_if_needed()
        return f"installation {action}"

    def on_installation_repositories(self) -> str:
        """Repositories were removed from an installation.

        Returns:
            What was done.
        """
        removed = [repo["id"] for repo in self.payload.get("repositories_removed", [])]
        Repository.objects.filter(github_id__in=removed).update(active=False)
        return f"{len(removed)} removed"

    def repository(self) -> Repository | None:
        """The active repository of the webhook.

        Returns:
            The repository, or None if it was not added.
        """
        repo = self.payload.get("repository") or {}
        found = (
            Repository.objects.filter(github_id=repo.get("id"), active=True)
            .select_related("installation")
            .first()
        )
        if found and repo.get("full_name") and found.full_name != repo["full_name"]:
            found.full_name = repo["full_name"]  # renamed or moved
            found.save(update_fields=["full_name"])
        return found

    def on_pull_request(self) -> str:
        """A pull request was opened or changed: check it.

        Returns:
            What was done.
        """
        repository = self.repository()
        if repository is None:
            return "repository not added"
        data = self.payload["pull_request"]
        action = self.payload.get("action", "")
        with transaction.atomic():
            pull, _ = PullRequest.objects.update_or_create(
                repository=repository,
                number=data["number"],
                defaults={
                    "title": (data.get("title") or "")[:500],
                    "author_github_id": data["user"]["id"],
                    "author_login": data["user"]["login"],
                    "head_sha": data["head"]["sha"],
                    "open": data.get("state", "open") == "open",
                    "merged": bool(data.get("merged")),
                },
            )
        if action not in PULL_ACTIONS or not pull.open:
            return f"pull request {action}"
        try:
            RepositorySync(repository).sync()
        except AgreementError as error:
            # the last agreements that could be read are kept and checked
            log.info("%s: %s", repository, error.code)
        PullRequestCheck(pull).run()
        return f"checked #{pull.number}"

    def on_repository(self) -> str:
        """A repository changed: its default branch, its name or its owner.

        A new default branch can hold another configuration: it is read again and the
        open pull requests are checked. A renamed or transferred repository keeps its id
        on GitHub; the site updates its name.

        Returns:
            What was done.
        """
        repository = self.repository()
        if repository is None:
            return "repository not added"
        action = self.payload.get("action", "")
        if action in ("renamed", "transferred"):
            # repository() already keeps the new name of every webhook
            return f"renamed to {repository.full_name}"
        changes = self.payload.get("changes") or {}
        if action == "edited" and "default_branch" in changes:
            RepositorySync(repository).sync()
            for pull in repository.pull_requests.filter(open=True):
                PullRequestCheck(pull).run()
            return "read again: new default branch"
        return f"repository {action}"

    def on_push(self) -> str:
        """A push to the default branch can change the configuration: read it again.

        Returns:
            What was done.
        """
        repository = self.repository()
        if repository is None:
            return "repository not added"
        default = self.payload["repository"].get("default_branch", "")
        if self.payload.get("ref") != f"refs/heads/{default}":
            return "not the default branch"
        changed = {
            path
            for commit in self.payload.get("commits", [])
            for key in ("added", "modified", "removed")
            for path in commit.get(key, [])
        }
        # an agreement of this repository changed: its tag may point to the new commit
        agreement_changed = repository.required_agreements.filter(
            version__source=repository.full_name, version__path__in=changed
        ).exists()
        if CONFIG_PATH not in changed and not agreement_changed:
            return "nothing to read again"
        RepositorySync(repository).sync()
        for pull in repository.pull_requests.filter(open=True):
            PullRequestCheck(pull).run()
        return "read again"
