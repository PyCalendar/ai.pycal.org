"""What a person may manage, asked of GitHub by the app itself, without a token of the person.

People sign in only with their identity. The app reads the installations and their
repositories with its own tokens, and the role of the person in each repository with
``GET /repos/{owner}/{repo}/collaborators/{username}/permission``, which needs only the
permission ``metadata: read``.
"""

from ai_pycal.errors import GitHubNotFound

from .app import GitHubApp

ROLES = ("admin", "maintain", "write", "triage", "read")


class RoleAPI:
    """The installations and repositories of the app, with the role of one person."""

    def __init__(self, login: str):
        """The roles of a person.

        Args:
            login: The GitHub handle of the person.
        """
        self.login = login
        self._repositories: dict[int, list[dict]] = {}

    def installations(self) -> list[dict]:
        """The installations of the app in which the person may push to a repository.

        Returns:
            The installations as GitHub describes them.
        """
        client = GitHubApp.app_client()
        found: list[dict] = []
        page = 1
        while True:
            data = client.get("/app/installations", per_page=100, page=page)
            found.extend(data)
            if len(data) < 100:
                break
            page += 1
        return [
            installation
            for installation in found
            if any(
                repo["permissions"].get("push") for repo in self.repositories(installation["id"])
            )
        ]

    def repositories(self, installation_id: int) -> list[dict]:
        """The repositories of an installation, each with the role of the person.

        Args:
            installation_id: The id of the installation.

        Returns:
            The repositories, each with ``permissions`` such as ``{"admin": true}``.
        """
        if installation_id in self._repositories:
            return self._repositories[installation_id]
        client = GitHubApp.for_installation(installation_id)
        found: list[dict] = []
        page = 1
        while True:
            data = client.get("/installation/repositories", per_page=100, page=page)
            found.extend(data.get("repositories", []))
            if len(found) >= data.get("total_count", 0) or not data.get("repositories"):
                break
            page += 1
        for repo in found:
            repo["permissions"] = self.permissions(client, repo["full_name"])
        self._repositories[installation_id] = found
        return found

    def permissions(self, client, full_name: str) -> dict[str, bool]:
        """The role of the person in a repository, as flags.

        Args:
            client: The requests of the installation.
            full_name: ``owner/name``.

        Returns:
            Such as ``{"admin": False, "maintain": True, "push": True}``; all False for
            people without access.
        """
        try:
            data = client.get(f"/repos/{full_name}/collaborators/{self.login}/permission")
        except GitHubNotFound:
            data = {}
        return self.flags(data.get("role_name") or data.get("permission") or "none")

    @staticmethod
    def flags(role: str) -> dict[str, bool]:
        """The flags of a role.

        Args:
            role: Such as ``admin``, ``maintain``, ``write`` or ``none``.

        Returns:
            ``admin``, ``maintain`` and ``push``.

        Examples:
            >>> RoleAPI.flags("maintain")
            {'admin': False, 'maintain': True, 'push': True}
            >>> RoleAPI.flags("read")
            {'admin': False, 'maintain': False, 'push': False}
        """
        rank = ROLES.index(role) if role in ROLES else len(ROLES)
        return {"admin": rank == 0, "maintain": rank <= 1, "push": rank <= 2}

    @staticmethod
    def can_administer(repository: dict) -> bool:
        """Whether the person has the role admin or maintain of a repository.

        Args:
            repository: A repository as :meth:`repositories` returns it.

        Returns:
            True if the person may set it up.

        Examples:
            >>> RoleAPI.can_administer({"permissions": {"maintain": True}})
            True
            >>> RoleAPI.can_administer({"permissions": {"push": True}})
            False
        """
        permissions = repository.get("permissions") or {}
        return bool(permissions.get("admin") or permissions.get("maintain"))
