"""The trigger of a webhook: what GitHub told the site, in words for people."""

from ai_pycal.config import CONFIG_PATH
from ai_pycal.models import LogTrigger, Repository


class WebhookTrigger:
    """Scope and describe the trigger of a webhook once it was handled."""

    @classmethod
    def complete(cls, trigger: LogTrigger, event: str, payload: dict, done: str) -> None:
        """Set the repository, pull request and summary of the trigger of a webhook.

        Webhooks of repositories that the site knows are public on their pages; others,
        such as installations, only in the global log.

        Args:
            trigger: The trigger.
            event: ``X-GitHub-Event``, such as ``push``.
            payload: The webhook.
            done: What the site did, from the handler, or the code of an error.
        """
        data = payload.get("repository") or {}
        repository = (
            Repository.objects.filter(github_id=data["id"]).first() if data.get("id") else None
        )
        pull_data = payload.get("pull_request") or {}
        trigger.repository = repository
        if repository and pull_data.get("number"):
            trigger.pull = repository.pull_requests.filter(number=pull_data["number"]).first()
        sender = payload.get("sender") or {}
        trigger.actor_login = (sender.get("login") or "")[:100]
        if pull_data.get("user", {}).get("id"):
            trigger.contributor_github_id = pull_data["user"]["id"]
        trigger.public = repository is not None
        trigger.summary = cls.describe(event, payload, done)[:300]
        trigger.save()

    @staticmethod
    def describe(event: str, payload: dict, done: str) -> str:
        """A webhook in words.

        Args:
            event: ``X-GitHub-Event``.
            payload: The webhook.
            done: What the site did.

        Returns:
            Such as ``Repository configuration updated`` or ``Pull request #3 opened: Fix``.

        Examples:
            >>> WebhookTrigger.describe("push", {"commits": [{"modified": [
            ...     ".github/agreements.yml"]}]}, "read again")
            'Repository configuration updated'
            >>> WebhookTrigger.describe("ping", {}, "pong")
            'Ping of GitHub'
        """
        action = payload.get("action", "")
        if event == "push":
            changed = {
                path
                for commit in payload.get("commits", [])
                for key in ("added", "modified", "removed")
                for path in commit.get(key, [])
            }
            if CONFIG_PATH in changed:
                return "Repository configuration updated"
            if done == "read again":
                return "Agreement updated in the repository"
            return "Push without changes of agreements"
        if event == "pull_request":
            pull = payload.get("pull_request") or {}
            return f"Pull request #{pull.get('number')} {action}: {pull.get('title', '')}"
        if event == "ping":
            return "Ping of GitHub"
        if event in ("installation", "installation_repositories"):
            account = ((payload.get("installation") or {}).get("account") or {}).get("login")
            return f"GitHub App {event.replace('_', ' ')} {action} by {account}"
        return f"Webhook {event} {action}".strip()
