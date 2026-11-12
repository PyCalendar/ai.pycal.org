"""The text of an agreement to show: the original, or its translation into the language."""

from dataclasses import dataclass

from django.utils.translation import get_language, get_language_info

from ai_pycal.models import AgreementTranslation, AgreementVersion

from .rendering import render as render_agreement


@dataclass
class AgreementText:
    """What the page of an agreement shows, and the note about its translation."""

    html: str
    translation: AgreementTranslation | None = None  # shown instead of the original
    available: AgreementTranslation | None = None  # offered while the original is shown

    @property
    def language_name(self) -> str:
        """The name of the language of the translation, in itself, such as ``Deutsch``."""
        found = self.translation or self.available
        if found is None:
            return ""
        name = get_language_info(found.language)["name_local"]
        return name[:1].upper() + name[1:]

    @classmethod
    def of(cls, version: AgreementVersion, request) -> "AgreementText":
        """The text of *version* for the language of the visitor.

        ``?original`` on the address shows the original instead of the translation.

        Args:
            version: The agreement.
            request: The request, with the language of the visitor.

        Returns:
            The text.
        """
        translation = version.translations.filter(language=get_language()).first()
        if translation is None:
            return cls(render_agreement(version.text, version.path))
        if "original" in request.GET:
            return cls(render_agreement(version.text, version.path), available=translation)
        return cls(render_agreement(translation.text, translation.path), translation=translation)
