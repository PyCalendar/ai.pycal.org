"""What the site reads from and writes to a repository, with the rights of an installation."""

import base64
import re
from urllib.parse import quote

from ai_pycal.errors import GitHubFileHistoryInvalid, GitHubNotFound

from .client import GitHubClient

MAX_FILE_BYTES = 200_000
STATUS_DESCRIPTION = 140  # the longest description of a commit status


class RepositoryAPI:
    """The requests about repositories and pull requests."""

    def __init__(self, client: GitHubClient):
        """The requests, sent with *client*.

        Args:
            client: A client with the token of an installation.
        """
        self.client = client

    def resolve(self, full_name: str, ref: str) -> str:
        """The commit of a tag, a branch or a commit.

        Args:
            full_name: ``owner/name`` of the repository.
            ref: The tag, branch or commit; "" for the default branch.

        Returns:
            The full SHA of the commit.

        Raises:
            GitHubNotFound: There is no such ref.
        """
        data = self.client.get(f"/repos/{full_name}/commits/{quote(ref or 'HEAD', safe='')}")
        return data["sha"]

    def file(self, full_name: str, commit: str, path: str) -> bytes:
        """The content of a file at a commit.

        Args:
            full_name: ``owner/name`` of the repository.
            commit: The commit.
            path: The path of the file.

        Returns:
            The bytes of the file.

        Raises:
            GitHubNotFound: There is no such file, or it is a directory.
        """
        data = self.client.get(f"/repos/{full_name}/contents/{quote(path)}", ref=commit)
        if not isinstance(data, dict) or data.get("type") != "file":
            raise GitHubNotFound(f"{full_name}/{path} is not a file")
        if data.get("encoding") == "base64" and data.get("content") is not None:
            return base64.b64decode(data["content"])
        # files above 1 MB come without content
        return b"\0" * (int(data.get("size", MAX_FILE_BYTES)) + 1)

    def last_file_change(self, full_name: str, commit: str, path: str) -> str:
        """Find the last edit of a file in the history of a resolved commit.

        Args:
            full_name: The source repository, owner/name.
            commit: An immutable SHA resolved from the configured reference.
            path: The agreement file's path in that repository.

        Returns:
            The SHA of the last commit affecting this path, including deletion.

        Raises:
            GitHubNotFound: This path has no history at the selected commit.
            GitHubFileHistoryInvalid: GitHub returned no valid commit identifier.
        """
        data = self.client.json(
            "GET",
            f"/repos/{full_name}/commits",
            params={"sha": commit, "path": path, "per_page": 1},
        )
        if data == []:
            raise GitHubNotFound(f"{full_name}/{path} has no history at {commit[:7]}")
        if (
            not isinstance(data, list)
            or not data
            or not isinstance(data[0], dict)
            or not isinstance(data[0].get("sha"), str)
            or not re.fullmatch(r"[0-9a-f]{40}", data[0]["sha"])
        ):
            raise GitHubFileHistoryInvalid(f"{full_name}/{path} at {commit[:7]}")
        return data[0]["sha"]

    def labels(self, full_name: str, number: int) -> list[str]:
        """The labels of a pull request.

        Args:
            full_name: ``owner/name`` of the repository.
            number: The number of the pull request.

        Returns:
            The names of the labels.
        """
        data = self.client.get(f"/repos/{full_name}/issues/{number}/labels", per_page=100)
        return [label["name"] for label in data]

    def add_labels(self, full_name: str, number: int, labels: list[str]) -> None:
        """Add labels to a pull request; GitHub creates labels that do not exist.

        Args:
            full_name: ``owner/name`` of the repository.
            number: The number of the pull request.
            labels: The names of the labels.
        """
        if labels:
            self.client.json(
                "POST", f"/repos/{full_name}/issues/{number}/labels", json={"labels": labels}
            )

    def remove_label(self, full_name: str, number: int, label: str) -> None:
        """Remove a label from a pull request; nothing if it is not there.

        Args:
            full_name: ``owner/name`` of the repository.
            number: The number of the pull request.
            label: The name of the label.
        """
        try:
            self.client.request(
                "DELETE", f"/repos/{full_name}/issues/{number}/labels/{quote(label, safe='')}"
            )
        except GitHubNotFound:
            pass

    def set_status(
        self, full_name: str, sha: str, context: str, state: str, description: str, url: str
    ) -> None:
        """Set a commit status, which GitHub shows as a check of the pull request.

        Args:
            full_name: ``owner/name`` of the repository.
            sha: The head commit of the pull request.
            context: The name of the check.
            state: ``success``, ``pending``, ``failure`` or ``error``.
            description: What it means, shortened to 140 characters.
            url: The page of the details.
        """
        if len(description) > STATUS_DESCRIPTION:
            description = description[: STATUS_DESCRIPTION - 1] + "…"
        self.client.json(
            "POST",
            f"/repos/{full_name}/statuses/{sha}",
            json={
                "state": state,
                "context": context,
                "description": description,
                "target_url": url,
            },
        )

    def installation_repositories(self) -> list[dict]:
        """The repositories of the installation of the client.

        Returns:
            The repositories as GitHub describes them.
        """
        found: list[dict] = []
        page = 1
        while True:
            data = self.client.get("/installation/repositories", per_page=100, page=page)
            found.extend(data.get("repositories", []))
            if len(found) >= data.get("total_count", 0) or not data.get("repositories"):
                return found
            page += 1

    def open_pulls(self, full_name: str) -> list[dict]:
        """The open pull requests of a repository, at most 300.

        Args:
            full_name: ``owner/name`` of the repository.

        Returns:
            The pull requests as GitHub describes them.
        """
        found: list[dict] = []
        for page in (1, 2, 3):
            data = self.client.get(
                f"/repos/{full_name}/pulls", state="open", per_page=100, page=page
            )
            found.extend(data)
            if len(data) < 100:
                break
        return found
