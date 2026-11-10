"""The GitHub account of a person who signed in."""

from dataclasses import dataclass

from allauth.socialaccount.models import SocialAccount

from .github_token import GitHubUserToken


@dataclass(frozen=True)
class GitHubIdentity:
    """The id and the handle of a GitHub account."""

    github_id: int
    login: str

    @classmethod
    def of(cls, user) -> "GitHubIdentity | None":
        """The GitHub account of a user of the site.

        Args:
            user: The user.

        Returns:
            The account; None for users without one, such as anonymous visitors.
        """
        if not getattr(user, "is_authenticated", False):
            return None
        account = SocialAccount.objects.filter(user=user, provider="github").first()
        if account is None:
            return None
        return cls(int(account.uid), str(account.extra_data.get("login") or user.username))

    @staticmethod
    def token(user) -> str:
        """The token of the sign in with GitHub, for the requests of administrators.

        Args:
            user: The user.

        Returns:
            The token; "" if there is none.
        """
        return GitHubUserToken.for_user(user)
