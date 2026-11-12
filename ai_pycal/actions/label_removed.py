"""A label removed from a pull request."""

from .action import Action


class LabelRemoved(Action):
    """Remove a label from a pull request on GitHub, with the reason."""

    kind = "label-removed"

    def __init__(self, api, pull, label: str, reason: str):
        """The label to remove.

        Args:
            api: The requests to GitHub of the repository.
            pull: The pull request.
            label: The label.
            reason: Why, such as ``CLA is not signed``.
        """
        super().__init__(pull=pull)
        self.api, self.label, self.reason = api, label, reason

    def perform(self) -> None:
        """Remove the label on GitHub."""
        self.api.remove_label(self.pull.repository.full_name, self.pull.number, self.label)

    def text(self) -> str:
        """Such as ``Label cla-signed removed from #3: CLA is not signed``."""
        return f"Label {self.label} removed from #{self.pull.number}: {self.reason}"
