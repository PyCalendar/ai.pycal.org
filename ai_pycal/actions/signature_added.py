"""A person signed an agreement."""

from .action import Action


class SignatureAdded(Action):
    """Record a signature: who signed which agreement."""

    kind = "signed"

    def __init__(self, signature, name: str):
        """The signature.

        Args:
            signature: The :class:`~ai_pycal.models.Signature`.
            name: The name of the agreement for people.
        """
        super().__init__(contributor_github_id=signature.github_id)
        self.login, self.name = signature.login, name

    def text(self) -> str:
        """Such as ``@alice signed CLA``."""
        return f"@{self.login} signed {self.name}"
