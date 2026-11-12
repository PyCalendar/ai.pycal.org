"""One agreement of a configuration file."""

import re
from dataclasses import dataclass

from ai_pycal.errors import (
    AgreementNotAMapping,
    InvalidAgreementField,
    InvalidAgreementId,
    InvalidAgreementPath,
    InvalidLabel,
    MissingAgreementField,
    UnknownConfigKey,
)

from .remote import GitHubRemote

AGREEMENT_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,49}$")
KEYS = {"name", "ref", "description", "mandatory", "repository", "path", "pr"}
MAX_LABEL = 50  # the longest label GitHub allows


@dataclass(frozen=True)
class AgreementSpec:
    """An agreement as a configuration file asks for it.

    The agreement is the file ``path`` of ``repository`` at ``tag``. Who signs it gets
    the labels ``labels`` on their pull requests; while a required agreement is not
    signed, the pull request has the labels ``unsigned_labels`` (format 2.1.0).
    """

    id: str
    name: str
    ref: str  # a tag, a branch or a commit; "" for the default branch
    repository: GitHubRemote
    path: str
    labels: tuple[str, ...]
    mandatory: bool = True
    description: str = ""
    unsigned_labels: tuple[str, ...] = ()

    @property
    def tag(self) -> str:
        """The reference under its legacy Python attribute name."""
        return self.ref

    @classmethod
    def parse(
        cls,
        agreement_id: object,
        data: object,
        home: GitHubRemote,
        strict: bool = True,
        legacy: bool = False,
    ) -> "AgreementSpec":
        """An agreement of a configuration file.

        Args:
            agreement_id: The key under ``agreements:``.
            data: The value under the key.
            home: The repository of the configuration file, the default of ``repository``.
            strict: Refuse unknown keys; False for files of a newer minor version.
            legacy: Read the version 1 names, tag and pr.tags.

        Returns:
            The agreement.

        Raises:
            InvalidAgreementId: The key is not an identifier.
            AgreementNotAMapping: The value is not a mapping.
            UnknownConfigKey: A key is unknown, in strict mode.
            MissingAgreementField: A required field is missing.
            InvalidAgreementField: A field has a value of the wrong kind.
            InvalidAgreementPath: The path is not relative or leaves the repository.
            InvalidLabel: A label is too long or empty.
            UnsupportedRemote: The repository is not on GitHub.

        Examples:
            >>> home = GitHubRemote("o", "r")
            >>> spec = AgreementSpec.parse("cla", {"name": "CLA", "path": "cla.md",
            ...     "pr": {"labels": "cla-signed"}}, home)
            >>> spec.repository.full_name, spec.labels, spec.ref
            ('o/r', ('cla-signed',), '')
        """
        if not isinstance(agreement_id, str) or not AGREEMENT_ID.match(agreement_id):
            raise InvalidAgreementId(f"agreements: {agreement_id!r}")
        if not isinstance(data, dict):
            raise AgreementNotAMapping(f"agreements.{agreement_id}")
        where = f"agreements.{agreement_id}"
        if strict:
            for key in data:
                if key not in (
                    KEYS - {"ref", "description", "mandatory"} | {"tag"} if legacy else KEYS
                ):
                    raise UnknownConfigKey(f"{where}.{key}")
        name = cls._text(data, "name", where, required=True)
        ref = cls._text(data, "tag" if legacy else "ref", where, required=False)
        mandatory = data.get("mandatory", True)
        if not isinstance(mandatory, bool):
            from ai_pycal.errors import InvalidMandatory

            raise InvalidMandatory(f"{where}.mandatory: expected true or false")
        description = data.get("description", "")
        if not isinstance(description, str):
            raise InvalidAgreementField(f"{where}.description: expected Markdown text")
        remote = cls._text(data, "repository", where, required=False)
        path = cls._path(cls._text(data, "path", where, required=True), where)
        return cls(
            id=agreement_id,
            name=name,
            ref=ref,
            repository=GitHubRemote.parse(remote) if remote else home,
            path=path,
            labels=cls._labels(data.get("pr"), where, strict, legacy),
            unsigned_labels=(
                () if legacy else cls._labels(data.get("pr"), where, False, field="unsigned-labels")
            ),
            mandatory=mandatory,
            description=description,
        )

    @staticmethod
    def _text(data: dict, key: str, where: str, required: bool) -> str:
        """A field of text.

        Args:
            data: The agreement.
            key: The field.
            where: The agreement, for the errors.
            required: Whether the field is required.

        Returns:
            The text without spaces around it, "" if it is missing and not required.

        Raises:
            MissingAgreementField: It is required and missing.
            InvalidAgreementField: It is not text.
        """
        value = data.get(key)
        if value is None or value == "":
            if required:
                raise MissingAgreementField(f"{where}.{key}")
            return ""
        if isinstance(value, bool) or not isinstance(value, str | int | float):
            raise InvalidAgreementField(f"{where}.{key}: expected text, got {value!r}")
        return str(value).strip()

    @staticmethod
    def _path(path: str, where: str) -> str:
        """The path of the agreement in its repository.

        Args:
            path: The value of ``path``.
            where: The agreement, for the errors.

        Returns:
            The path.

        Raises:
            InvalidAgreementPath: It is absolute, a directory or contains ``..``.

        Examples:
            >>> AgreementSpec._path("docs/../x.md", "a")
            Traceback (most recent call last):
            ...
            ai_pycal.errors.config_file.InvalidAgreementPath: a.path: 'docs/../x.md'
        """
        parts = path.split("/")
        if path.startswith("/") or path.endswith("/") or ".." in parts or "" in parts:
            raise InvalidAgreementPath(f"{where}.path: {path!r}")
        return path

    @staticmethod
    def _labels(
        pr: object, where: str, strict: bool, legacy: bool = False, field: str = ""
    ) -> tuple[str, ...]:
        """The pull request labels: one label or a list of labels.

        Args:
            pr: The value of ``pr``.
            where: The agreement, for the errors.
            strict: Refuse unknown keys.
            legacy: Read tags instead of labels.
            field: The field of ``pr`` to read: ``labels`` (labels of signed agreements,
                the default) or ``unsigned-labels`` (labels while unsigned).

        Returns:
            The labels, without duplicates.

        Raises:
            MissingAgreementField: There is no ``pr.tags``.
            InvalidAgreementField: ``pr`` is no mapping or a label is not text.
            InvalidLabel: A label is empty or too long.
            UnknownConfigKey: ``pr`` has a key other than ``tags``, in strict mode.

        Examples:
            >>> AgreementSpec._labels({"labels": ["a", "b", "a"]}, "x", True)
            ('a', 'b')
            >>> AgreementSpec._labels({"unsigned-labels": "x"}, "x", True, field="unsigned-labels")
            ('x',)
        """
        field = field or ("tags" if legacy else "labels")
        if pr is None and not legacy:
            return ()
        if pr is None:
            raise MissingAgreementField(f"{where}.pr.tags")
        if not isinstance(pr, dict):
            raise InvalidAgreementField(f"{where}.pr: expected a mapping with tags")
        if strict:
            known = {"tags"} if legacy else {"labels", "unsigned-labels"}
            for key in pr:
                if key not in known:
                    raise UnknownConfigKey(f"{where}.pr.{key}")
        tags = pr.get(field)
        if not legacy and (tags is None or tags == []):
            return ()
        if tags is None or tags == []:
            raise MissingAgreementField(f"{where}.pr.{field}")
        tags = [tags] if isinstance(tags, str) else tags
        if not isinstance(tags, list):
            raise InvalidAgreementField(f"{where}.pr.{field}: expected a label or a list of labels")
        labels: list[str] = []
        for tag in tags:
            if not isinstance(tag, str):
                raise InvalidAgreementField(f"{where}.pr.{field}: {tag!r} is not text")
            label = tag.strip()
            if not label or len(label) > MAX_LABEL:
                raise InvalidLabel(f"{where}.pr.{field}: {tag!r}")
            if label not in labels:
                labels.append(label)
        return tuple(labels)
