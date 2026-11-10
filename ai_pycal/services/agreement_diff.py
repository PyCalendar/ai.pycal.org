"""What changed between two versions of an agreement."""

import difflib
from dataclasses import dataclass

from ai_pycal.models import AgreementVersion, Signature


@dataclass(frozen=True)
class DiffLine:
    """A line of the difference: ``added``, ``removed``, ``same`` or ``skip``."""

    kind: str
    text: str


class AgreementDiff:
    """The difference between a version someone signed and the one asked for now."""

    def __init__(self, old: AgreementVersion, new: AgreementVersion):
        """The difference from *old* to *new*.

        Args:
            old: The version signed before.
            new: The version asked for.
        """
        self.old = old
        self.new = new

    @staticmethod
    def lines(old: str, new: str, context: int = 3) -> list[DiffLine]:
        r"""The lines that changed, with some lines around them.

        Args:
            old: The old text.
            new: The new text.
            context: How many unchanged lines are shown around changes.

        Returns:
            The lines.

        Examples:
            >>> [(line.kind, line.text) for line in AgreementDiff.lines("a\nb\n", "a\nc\n")]
            [('same', 'a'), ('removed', 'b'), ('added', 'c')]
        """
        result: list[DiffLine] = []
        diff = difflib.unified_diff(old.splitlines(), new.splitlines(), n=context, lineterm="")
        for line in diff:
            if line.startswith(("---", "+++")):
                continue
            if line.startswith("@@"):
                if result:
                    result.append(DiffLine("skip", "…"))
                continue
            kind = {"+": "added", "-": "removed"}.get(line[:1], "same")
            result.append(DiffLine(kind, line[1:]))
        return result

    def changes(self) -> list[DiffLine]:
        """The lines that changed between the two versions.

        Returns:
            The lines.
        """
        return self.lines(self.old.text, self.new.text)

    @staticmethod
    def previous_signed(version: AgreementVersion, github_id: int) -> AgreementVersion | None:
        """The last other version of the same file that a person signed.

        Args:
            version: The version asked for.
            github_id: The person.

        Returns:
            The version signed last; None if the person never signed this file.
        """
        signature = (
            Signature.objects.filter(
                github_id=github_id, version__source=version.source, version__path=version.path
            )
            .exclude(version=version)
            .select_related("version")
            .order_by("-signed")
            .first()
        )
        return signature.version if signature else None
