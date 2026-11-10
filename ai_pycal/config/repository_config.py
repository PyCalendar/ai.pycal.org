"""The configuration file of a repository."""

from dataclasses import dataclass

import yaml

from ai_pycal.errors import (
    ConfigFileNotAMapping,
    ConfigFileNotYAML,
    ConfigVersionMissing,
    NoAgreements,
    UnknownConfigKey,
)

from .agreement_spec import AgreementSpec
from .choice_spec import ChoiceSpec
from .format_version import SUPPORTED, FormatVersion
from .remote import GitHubRemote

# where the file is in the default branch of a repository
CONFIG_PATH = ".github/agreements.yml"
KEYS = {"version", "agreements"}


@dataclass(frozen=True)
class RepositoryConfig:
    """What a repository asks of the people who open pull requests."""

    version: FormatVersion
    agreements: tuple[AgreementSpec, ...]
    newer: bool = False  # written for a newer minor version: unknown keys were ignored
    choices: tuple[ChoiceSpec, ...] = ()

    @classmethod
    def parse(cls, text: str, home: GitHubRemote) -> "RepositoryConfig":
        """Read a configuration file.

        Args:
            text: The content of the file.
            home: The repository of the file.

        Returns:
            The configuration.

        Raises:
            ConfigFileNotYAML: It is no YAML.
            ConfigFileNotAMapping: It is no mapping.
            ConfigVersionMissing: There is no version.
            ConfigVersionInvalid: The version is not a version.
            ConfigVersionUnsupported: The major version is unknown.
            UnknownConfigKey: A key is unknown.
            NoAgreements: There are no agreements.

        Examples:
            >>> config = RepositoryConfig.parse('''
            ... version: 1.0.0
            ... agreements:
            ...   ai-policy:
            ...     name: AI policy
            ...     tag: v1
            ...     path: AI.md
            ...     pr:
            ...       tags: [ai-policy]
            ... ''', GitHubRemote("o", "r"))
            >>> [spec.id for spec in config.agreements]
            ['ai-policy']
        """
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as error:
            raise ConfigFileNotYAML(str(error)) from error
        if not isinstance(data, dict):
            raise ConfigFileNotAMapping(f"{CONFIG_PATH}: {type(data).__name__}")
        if "version" not in data:
            raise ConfigVersionMissing(CONFIG_PATH)
        version = FormatVersion.parse(data["version"])
        newer = version.check_supported(SUPPORTED)
        if not newer:
            for key in data:
                if key not in (KEYS | ({"choices"} if version.major == 2 else set())):
                    raise UnknownConfigKey(str(key))
        agreements = data.get("agreements")
        if not agreements:
            raise NoAgreements(CONFIG_PATH)
        if not isinstance(agreements, dict):
            raise NoAgreements(f"agreements: expected a mapping, got {type(agreements).__name__}")
        specs = tuple(
            AgreementSpec.parse(key, value, home, strict=not newer, legacy=version.major == 1)
            for key, value in agreements.items()
        )
        from ai_pycal.errors.choices import (
            DuplicateChoice,
            InvalidChoices,
            MultipleDefaultChoices,
        )

        choices = data.get("choices", []) if version.major == 2 else []
        if not isinstance(choices, list):
            raise InvalidChoices()
        parsed = tuple(
            ChoiceSpec.parse(choice, {s.id for s in specs}, not newer) for choice in choices
        )
        if len({choice.key for choice in parsed}) != len(parsed):
            raise DuplicateChoice()
        if sum(choice.default for choice in parsed) > 1:
            raise MultipleDefaultChoices()
        return cls(version=version, agreements=specs, newer=newer, choices=parsed)
