"""The base of the actions: do the effect, then record it in the log."""

from ai_pycal.models import LogAction

from .trigger import Trigger


class Action:
    """An effect of the site and its record in the log.

    Subclasses set ``kind``, describe themselves in :meth:`text` and do their effect in
    :meth:`perform`; :meth:`run` does both. ``public`` actions are shown on the pages of
    their repository, pull request and contributor; the others only in the global log.
    """

    kind = "action"
    public = True

    def __init__(self, repository=None, pull=None, contributor_github_id=None):
        """An action concerning a repository, a pull request or a contributor.

        Args:
            repository: The repository, or None.
            pull: The pull request, or None; its repository and author are used if unset.
            contributor_github_id: The person, or None.
        """
        self.pull = pull
        self.repository = repository or (pull.repository if pull else None)
        self.contributor_github_id = contributor_github_id or (
            pull.author_github_id if pull else None
        )

    def text(self) -> str:
        """What was done and why, for people."""
        raise NotImplementedError

    def perform(self) -> None:
        """Do the effect; records without an effect do nothing."""

    def run(self) -> "Action":
        """Do the effect and record it in the current trigger.

        Returns:
            The action.
        """
        self.perform()
        LogAction.objects.create(
            trigger=Trigger.current(),
            kind=self.kind,
            text=self.text()[:500],
            repository=self.repository,
            pull=self.pull,
            contributor_github_id=self.contributor_github_id,
            public=self.public,
        )
        return self
