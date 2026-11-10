"""One alternative policy bundle offered by a project."""

from dataclasses import dataclass

from django.utils.text import slugify

from ai_pycal.errors.choices import (
    ChoiceNotAMapping,
    InvalidChoiceAgreements,
    InvalidChoiceDefault,
    InvalidChoiceDescription,
    InvalidChoiceName,
    UnknownChoiceAgreement,
)
from ai_pycal.errors.config_file import UnknownConfigKey

from .agreement_spec import AgreementSpec


@dataclass(frozen=True)
class ChoiceSpec:
    """A named bundle of agreements and the labels it grants."""

    key: str
    name: str
    description: str
    agreements: tuple[str, ...]
    default: bool
    labels: tuple[str, ...]

    @classmethod
    def parse(cls, data: object, known: set[str], strict: bool = True) -> "ChoiceSpec":
        """Validate a choice against the agreements defined by its project.

        Args:
            data: A mapping from the choices list.
            known: Available agreement identifiers.
            strict: Whether unknown fields are rejected.

        Returns:
            The validated choice.

        Raises:
            InvalidChoiceField: A field is missing or has the wrong type.
            UnknownChoiceAgreement: An agreement identifier is not defined.
            UnknownConfigKey: An unrecognized field is present.
        """
        if not isinstance(data, dict):
            raise ChoiceNotAMapping("choices: expected a mapping")
        if strict:
            for key in data:
                if key not in {"name", "description", "agreements", "default", "pr"}:
                    raise UnknownConfigKey(f"choices.{key}")
        name = data.get("name")
        description = data.get("description")
        agreements = data.get("agreements")
        default = data.get("default", False)
        if not isinstance(name, str) or not name.strip() or len(name) > 200:
            raise InvalidChoiceName("choices.name: expected a name of at most 200 characters")
        key = slugify(name)
        if not key or len(key) > 50:
            raise InvalidChoiceName(
                f"choices.{name}: name must produce an identifier of at most 50 characters"
            )
        if not isinstance(description, str) or not description.strip():
            raise InvalidChoiceDescription(f"choices.{name}.description: expected Markdown text")
        if not isinstance(default, bool):
            raise InvalidChoiceDefault(f"choices.{name}.default: expected true or false")
        if not isinstance(agreements, list) or not agreements:
            raise InvalidChoiceAgreements(f"choices.{name}.agreements: expected a nonempty list")
        for agreement in agreements:
            if not isinstance(agreement, str) or agreement not in known:
                raise UnknownChoiceAgreement(f"choices.{name}.agreements: {agreement!r}")
        return cls(
            key,
            name.strip(),
            description,
            tuple(dict.fromkeys(agreements)),
            default,
            AgreementSpec._labels(data.get("pr"), f"choices.{name}", strict, legacy=False),
        )
