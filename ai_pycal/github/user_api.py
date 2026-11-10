"""What the site asks GitHub with the token of a person who signed in."""

from .client import GitHubClient


class UserAPI:
    """The installations and repositories a person may manage."""

    def __init__(self, token: str):
        """The requests with the token of a person.

        Args:
            token: The token of the sign in with GitHub.
        """
        self.client = GitHubClient(token)

    def installations(self) -> list[dict]:
        """The installations of the app that the person can access.

        Returns:
            The installations as GitHub describes them.
        """
        data = self.client.get("/user/installations", per_page=100)
        return data.get("installations", [])

    def repositories(self, installation_id: int) -> list[dict]:
        """The repositories of an installation that the person can access, with their role.

        Args:
            installation_id: The id of the installation.

        Returns:
            The repositories, each with ``permissions`` such as ``{"admin": true}``.
        """
        found: list[dict] = []
        page = 1
        while True:
            data = self.client.get(
                f"/user/installations/{installation_id}/repositories", per_page=100, page=page
            )
            found.extend(data.get("repositories", []))
            if len(found) >= data.get("total_count", 0) or not data.get("repositories"):
                return found
            page += 1

    @staticmethod
    def can_administer(repository: dict) -> bool:
        """Whether the person has the role admin or maintain of a repository.

        Args:
            repository: A repository as :meth:`repositories` returns it.

        Returns:
            True if the person may set it up.

        Examples:
            >>> UserAPI.can_administer({"permissions": {"maintain": True}})
            True
            >>> UserAPI.can_administer({"permissions": {"push": True}})
            False
        """
        permissions = repository.get("permissions") or {}
        return bool(permissions.get("admin") or permissions.get("maintain"))
