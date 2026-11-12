"""Read the version of an agreement that a configuration file asks for."""

import logging
import posixpath

from django.conf import settings

from ai_pycal.config import AgreementSpec
from ai_pycal.errors import (
    AgreementFileNotFound,
    AgreementFileNotText,
    AgreementFileTooLarge,
    AgreementRefNotFound,
    AgreementTitleMissing,
    GitHubError,
    GitHubNotFound,
)
from ai_pycal.github.repository_api import MAX_FILE_BYTES, RepositoryAPI
from ai_pycal.models import AgreementTranslation, AgreementVersion
from ai_pycal.services.rendering import markdown_title

log = logging.getLogger(__name__)


class AgreementFetcher:
    """Identify an agreement by its last file edit within the selected reference."""

    def __init__(self, api: RepositoryAPI):
        """The fetcher, reading with *api*.

        Args:
            api: The requests, with the rights of the installation.
        """
        self.api = api

    def fetch(self, spec: AgreementSpec) -> AgreementVersion:
        """Read the version identified by the agreement file's last edit.

        A version that was read before is not read again: the text of a commit never
        changes.

        Args:
            spec: The agreement of the configuration file.

        Returns:
            The version, saved.

        Raises:
            AgreementRefNotFound: The reference does not exist.
            AgreementFileNotFound: The file does not exist at the commit.
            AgreementFileTooLarge: The file is larger than 200 KB.
            AgreementFileNotText: The file is not UTF-8.
        """
        source = spec.repository.full_name
        try:
            snapshot = self.api.resolve(source, spec.ref)
        except GitHubNotFound as error:
            raise AgreementRefNotFound(
                f"agreements.{spec.id}: ref {spec.ref or '(default branch)'!r} in {source}"
            ) from error
        try:
            commit, committed = self.api.file_change(source, snapshot, spec.path)
        except GitHubNotFound as error:
            raise AgreementFileNotFound(
                f"agreements.{spec.id}: {spec.path} in {source} at {snapshot[:7]}"
            ) from error
        known = AgreementVersion.objects.filter(
            source=source, commit=commit, path=spec.path
        ).first()
        if known:
            if committed and not known.committed:  # read before the time was kept
                known.committed = committed
                known.save(update_fields=["committed"])
            self.read_translations(known, snapshot)
            return known
        try:
            content = self.api.file(source, commit, spec.path)
        except GitHubNotFound as error:
            raise AgreementFileNotFound(
                f"agreements.{spec.id}: {spec.path} in {source} at {commit[:7]}"
            ) from error
        if len(content) > MAX_FILE_BYTES:
            raise AgreementFileTooLarge(f"agreements.{spec.id}: {len(content)} bytes")
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise AgreementFileNotText(f"agreements.{spec.id}: {spec.path}") from error
        if "\0" in text:
            raise AgreementFileNotText(f"agreements.{spec.id}: {spec.path}")
        title = markdown_title(text)
        if not title:
            raise AgreementTitleMissing(f"agreements.{spec.id}: {spec.path} has no # heading")
        version, _ = AgreementVersion.objects.get_or_create(
            source=source,
            commit=commit,
            path=spec.path,
            defaults={"text": text, "committed": committed, "title": title},
        )
        self.read_translations(version, snapshot)
        return version

    @staticmethod
    def translation_path(path: str, language: str) -> str:
        """The file of the translation of an agreement into a language.

        Args:
            path: The file of the agreement.
            language: Such as ``de``.

        Returns:
            The file next to it.

        Examples:
            >>> AgreementFetcher.translation_path("agreements/cla.md", "de")
            'agreements/cla.de.md'
            >>> AgreementFetcher.translation_path("POLICY", "es")
            'POLICY.es'
        """
        root, extension = posixpath.splitext(path)
        return f"{root}.{language}{extension}"

    def read_translations(self, version: AgreementVersion, snapshot: str) -> None:
        """Read the translations next to the file of an agreement, at *snapshot*.

        A translation that is missing is removed; one that cannot be read is logged and
        left out, so that it never stops the configuration.

        Args:
            version: The agreement.
            snapshot: The commit of the reference of the configuration.
        """
        for language, _ in settings.LANGUAGES:
            path = self.translation_path(version.path, language)
            try:
                content = self.api.file(version.source, snapshot, path)
            except GitHubNotFound:
                version.translations.filter(language=language).delete()
                continue
            except GitHubError as error:  # a passing error: the translation read before stays
                log.warning("%s/%s: %s", version.source, path, error.code)
                continue
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                text = ""
            if not text or "\0" in text or len(content) > MAX_FILE_BYTES:
                log.warning("%s/%s: the translation cannot be read", version.source, path)
                continue
            AgreementTranslation.objects.update_or_create(
                version=version,
                language=language,
                defaults={
                    "path": path,
                    "commit": snapshot,
                    "text": text,
                    "title": markdown_title(text) or "",
                },
            )
