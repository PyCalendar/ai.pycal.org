"""A label added to a pull request."""

from .action import Action


class LabelAdded(Action):
    """Add a label to a pull request on GitHub, with the reason."""

    kind = "label-added"

    def __init__(self, api, pull, label: str, reason: str):
        """The label to add.

        Args:
            api: The requests to GitHub of the repository.
            pull: The pull request.
            label: The label.
            reason: Why, such as ``CLA is signed``.
        """
        super().__init__(pull=pull)
        self.api, self.label, self.reason = api, label, reason

    def perform(self) -> None:
        """Add the label on GitHub."""
        self.api.add_labels(self.pull.repository.full_name, self.pull.number, [self.label])

    def text(self) -> str:
        """Such as ``Label cla-signed added to #3: CLA is signed``."""
        return f"Label {self.label} added to #{self.pull.number}: {self.reason}"
