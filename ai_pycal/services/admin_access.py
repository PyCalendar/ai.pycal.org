"""What an administrator may set up: asked of GitHub with the token of their sign in."""

from ai_pycal.errors import GitHubLoginExpired, InstallationNotYours, NotRepositoryAdmin
from ai_pycal.github.app import GitHubApp
from ai_pycal.github.user_api import UserAPI
from ai_pycal.models import Installation, Repository

from .identity import GitHubIdentity
from .webhook_handler import WebhookHandler


class AdminAccess:
    """The installations and repositories a person manages on GitHub.

    GitHub decides: an installation is listed if the person can access it, and a
    repository can be set up by people with the role admin or maintain.
    """

    def __init__(self, user, api: UserAPI | None = None):
        """The access of *user*.

        Args:
            user: The user of the site.
            api: The requests with the token of the user; made from the token by default.

        Raises:
            GitHubLoginExpired: There is no token: sign in again.
        """
        self.user = user
        if api is None:
            token = GitHubIdentity.token(user)
            if not token:
                raise GitHubLoginExpired("no token")
            api = UserAPI(token)
        self.api = api

    def installations(self) -> list[dict]:
        """The installations the person can access.

        Returns:
            The installations as GitHub describes them.
        """
        return self.api.installations()

    def installation(self, installation_id: int) -> Installation:
        """An installation the person can access, stored and with them as administrator.

        Args:
            installation_id: The id of the installation on GitHub.

        Returns:
            The installation.

        Raises:
            InstallationNotYours: The person can not access it.
        """
        if not any(found["id"] == installation_id for found in self.installations()):
            raise InstallationNotYours(str(installation_id))
        installation = WebhookHandler.store_installation(GitHubApp.installation(installation_id))
        installation.admins.add(self.user)
        return installation

    def repositories(self, installation_id: int) -> list[dict]:
        """The repositories of an installation that the person can access.

        Args:
            installation_id: The id of the installation on GitHub.

        Returns:
            The repositories, with ``can_administer`` and the ``stored`` repository.
        """
        found = self.api.repositories(installation_id)
        stored = {
            repo.github_id: repo
            for repo in Repository.objects.filter(github_id__in=[r["id"] for r in found])
        }
        for repo in found:
            repo["can_administer"] = UserAPI.can_administer(repo)
            repo["stored"] = stored.get(repo["id"])
            if repo["stored"] and any(
                (repo.get("permissions") or {}).get(role) for role in ("admin", "maintain", "push")
            ):
                repo["stored"].watchers.add(self.user)
        return found

    def repository(self, installation_id: int, repository_id: int) -> Repository:
        """A repository that the person administers, stored.

        Args:
            installation_id: The id of the installation on GitHub.
            repository_id: The id of the repository on GitHub.

        Returns:
            The repository; not yet active if it is new.

        Raises:
            InstallationNotYours: The person can not access the installation.
            NotRepositoryAdmin: The person does not administer the repository.
        """
        installation = self.installation(installation_id)
        for repo in self.api.repositories(installation_id):
            if repo["id"] == repository_id:
                if not UserAPI.can_administer(repo):
                    raise NotRepositoryAdmin(repo["full_name"])
                stored, _ = Repository.objects.update_or_create(
                    github_id=repository_id,
                    defaults={
                        "installation": installation,
                        "full_name": repo["full_name"],
                        "private": bool(repo.get("private")),
                    },
                )
                stored.watchers.add(self.user)
                return stored
        raise NotRepositoryAdmin(str(repository_id))
