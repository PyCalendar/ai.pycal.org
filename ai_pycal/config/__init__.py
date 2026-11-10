"""The configuration file of a repository, ``.github/agreements.yml``, and what it names."""

from .agreement_spec import AgreementSpec
from .format_version import SUPPORTED, FormatVersion
from .remote import GitHubRemote
from .repository_config import CONFIG_PATH, RepositoryConfig

__all__ = [
    "CONFIG_PATH",
    "SUPPORTED",
    "AgreementSpec",
    "FormatVersion",
    "GitHubRemote",
    "RepositoryConfig",
]
