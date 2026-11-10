"""A repository on GitHub, named by a git remote."""

import re
from dataclasses import dataclass

from ai_pycal.errors import UnsupportedRemote

NAME = r"[A-Za-z0-9_.-]+"
REMOTES = [
    re.compile(
        rf"^(?:https?://|git://)(?:www\.)?github\.com/(?P<owner>{NAME})/(?P<name>{NAME})/?$"
    ),
    re.compile(rf"^(?:ssh://)?git@github\.com[:/](?P<owner>{NAME})/(?P<name>{NAME})$"),
    re.compile(rf"^(?P<owner>{NAME})/(?P<name>{NAME})$"),
]


@dataclass(frozen=True)
class GitHubRemote:
    """A repository on GitHub."""

    owner: str
    name: str

    @classmethod
    def parse(cls, remote: str) -> "GitHubRemote":
        """The repository of a git remote of GitHub.

        Args:
            remote: The address as ``git remote`` shows it, or ``owner/name``.

        Returns:
            The repository.

        Raises:
            UnsupportedRemote: The remote is not on GitHub.

        Examples:
            >>> GitHubRemote.parse("https://github.com/PyCalendar/ai.pycal.org-example.git")
            GitHubRemote(owner='PyCalendar', name='ai.pycal.org-example')
            >>> GitHubRemote.parse("git@github.com:PyCalendar/icalendar.git").full_name
            'PyCalendar/icalendar'
            >>> GitHubRemote.parse("PyCalendar/icalendar").url
            'https://github.com/PyCalendar/icalendar'
        """
        text = str(remote).strip()
        for pattern in REMOTES:
            match = pattern.match(text)
            if match:
                name = match["name"].removesuffix(".git")
                if name and name not in {".", ".."}:
                    return cls(match["owner"], name)
        raise UnsupportedRemote(f"repository: {text!r}")

    @property
    def full_name(self) -> str:
        """The name as GitHub writes it: ``owner/name``."""
        return f"{self.owner}/{self.name}"

    @property
    def url(self) -> str:
        """The page of the repository on GitHub."""
        return f"https://github.com/{self.full_name}"

    def file_url(self, commit: str, path: str) -> str:
        """The page of a file of the repository at a commit.

        Args:
            commit: The commit.
            path: The path of the file in the repository.

        Returns:
            The address on GitHub.

        Examples:
            >>> GitHubRemote("o", "r").file_url("abc", "a/b.md")
            'https://github.com/o/r/blob/abc/a/b.md'
        """
        return f"{self.url}/blob/{commit}/{path}"
