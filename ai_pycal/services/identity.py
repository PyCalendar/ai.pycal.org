"""The GitHub account of a person who signed in."""

from dataclasses import dataclass

from allauth.socialaccount.models import SocialAccount


@dataclass(frozen=True)
class GitHubIdentity:
    """The id and the handle of a GitHub account."""

    github_id: int
    login: str

    @classmethod
    def is_site_admin(cls, user) -> bool:
        """Whether a person administers the site: their GitHub handle is in ``SITE_ADMINS``.

        Args:
            user: The user.

        Returns:
            True for administrators of the site.
        """
        from django.conf import settings

        identity = cls.of(user)
        return bool(identity and identity.login.lower() in settings.SITE_ADMINS)

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
