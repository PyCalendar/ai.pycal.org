"""What an administrator may set up: asked of GitHub by the app, with the role of the person."""

from ai_pycal.errors import GitHubLoginExpired, InstallationNotYours, NotRepositoryAdmin
from ai_pycal.github.app import GitHubApp
from ai_pycal.github.role_api import RoleAPI
from ai_pycal.models import Installation, Repository

from .identity import GitHubIdentity
from .webhook_handler import WebhookHandler


class AdminAccess:
    """The installations and repositories a person manages on GitHub.

    GitHub decides: an installation is listed if the person can access it, and a
    repository can be set up by people with the role admin or maintain.
    """

    def __init__(self, user, api: RoleAPI | None = None):
        """The access of *user*.

        Args:
            user: The user of the site.
            api: The requests of the app with the role of the user; by default for the
                GitHub account of the user.

        Raises:
            GitHubLoginExpired: The user did not sign in with GitHub.
        """
        self.user = user
        if api is None:
            identity = GitHubIdentity.of(user)
            if identity is None:
                raise GitHubLoginExpired("no GitHub account")
            api = RoleAPI(identity.login)
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
            repo["can_administer"] = RoleAPI.can_administer(repo)
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
                if not RoleAPI.can_administer(repo):
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
