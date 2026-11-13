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
    def keep_rights(cls, user) -> bool:
        """Give the people of ``SITE_ADMINS`` the rights of the Django admin, and only them.

        Users without a GitHub account, such as one of ``createsuperuser``, keep their rights.

        Args:
            user: The user.

        Returns:
            True if the rights changed.
        """
        from django.conf import settings

        identity = cls.of(user)
        if identity is None:
            return False
        admin = identity.login.lower() in settings.SITE_ADMINS
        if user.is_staff == admin and user.is_superuser == admin:
            return False
        user.is_staff = user.is_superuser = admin
        user.save(update_fields=["is_staff", "is_superuser"])
        return True

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
