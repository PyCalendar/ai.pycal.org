"""A repository asks for a new version of an agreement."""

from .action import Action


class AgreementChanged(Action):
    """Record that the version of an agreement that a repository asks for changed."""

    kind = "agreement-changed"

    def __init__(self, repository, name: str, version):
        """The new version.

        Args:
            repository: The repository that asks for the agreement.
            name: The name of the agreement.
            version: The new :class:`~ai_pycal.models.AgreementVersion`.
        """
        super().__init__(repository=repository)
        self.name, self.version = name, version

    def text(self) -> str:
        """Such as ``New version of CLA: 2026-11-12 09:30 UTC; signatures are needed again``."""
        when = (self.version.committed or self.version.fetched).strftime("%Y-%m-%d %H:%M UTC")
        return f"New version of {self.name}: {when}; signatures are needed again"
