"""Read the version of an agreement that a configuration file asks for."""

from ai_pycal.config import AgreementSpec
from ai_pycal.errors import (
    AgreementFileNotFound,
    AgreementFileNotText,
    AgreementFileTooLarge,
    AgreementRefNotFound,
    GitHubNotFound,
)
from ai_pycal.github.repository_api import MAX_FILE_BYTES, RepositoryAPI
from ai_pycal.models import AgreementVersion


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
            commit = self.api.last_file_change(source, snapshot, spec.path)
        except GitHubNotFound as error:
            raise AgreementFileNotFound(
                f"agreements.{spec.id}: {spec.path} in {source} at {snapshot[:7]}"
            ) from error
        known = AgreementVersion.objects.filter(
            source=source, commit=commit, path=spec.path
        ).first()
        if known:
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
        version, _ = AgreementVersion.objects.get_or_create(
            source=source, commit=commit, path=spec.path, defaults={"text": text}
        )
        return version
