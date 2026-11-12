"""A check of a pull request: its commit status on GitHub."""

from .action import Action


class StatusSet(Action):
    """Set a commit status of the head of a pull request on GitHub."""

    kind = "status"

    def __init__(self, api, pull, context: str, state: str, description: str, url: str):
        """The status to set.

        Args:
            api: The requests to GitHub of the repository.
            pull: The pull request.
            context: The name of the check, such as ``sign.pycal.org/cla``.
            state: ``success``, ``pending`` or ``error``.
            description: The text of the check.
            url: Where the check links to.
        """
        super().__init__(pull=pull)
        self.api, self.context, self.state = api, context, state
        self.description, self.url = description, url

    def perform(self) -> None:
        """Set the status on GitHub."""
        self.api.set_status(
            self.pull.repository.full_name,
            self.pull.head_sha,
            self.context,
            self.state,
            self.description,
            self.url,
        )

    def text(self) -> str:
        """Such as ``Check sign.pycal.org/cla of #3: pending, @alice: please sign CLA``."""
        return f"Check {self.context} of #{self.pull.number}: {self.state}, {self.description}"
