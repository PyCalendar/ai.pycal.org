"""The configuration of a repository was read."""

from .action import Action


class ConfigurationRead(Action):
    """Record that the configuration file of a repository was read, or why it failed."""

    kind = "configuration"

    def __init__(self, repository, version: str = "", agreements: int = 0, error=None):
        """The result of reading the configuration.

        Args:
            repository: The repository.
            version: The version of the format of the file.
            agreements: How many agreements it asks for.
            error: The error, if the file could not be used.
        """
        super().__init__(repository=repository)
        self.version, self.agreements, self.error = version, agreements, error

    def text(self) -> str:
        """Such as ``Configuration 2.1.0 read: 2 agreements``."""
        if self.error is not None:
            return f"Configuration could not be read: {self.error.title} ({self.error.code})"
        return f"Configuration {self.version} read: {self.agreements} agreements"
