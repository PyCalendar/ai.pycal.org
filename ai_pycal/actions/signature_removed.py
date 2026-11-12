"""An administrator of the site removed their own signature, to test what follows."""

from .action import Action


class SignatureRemoved(Action):
    """Remove a signature of the person themselves and record it."""

    kind = "signature-removed"

    def __init__(self, signature, name: str):
        """The signature to remove.

        Args:
            signature: The :class:`~ai_pycal.models.Signature`.
            name: The name of the agreement for people.
        """
        super().__init__(contributor_github_id=signature.github_id)
        self.signature, self.login, self.name = signature, signature.login, name

    def perform(self) -> None:
        """Delete the signature."""
        self.signature.delete()

    def text(self) -> str:
        """Such as ``@alice removed their signature of CLA``."""
        return f"@{self.login} removed their signature of {self.name}"
