"""Who signs in with GitHub: the handle becomes the user name; SITE_ADMINS administer."""

from allauth.account.signals import user_logged_in
from django.conf import settings
from django.dispatch import receiver

from .services.identity import GitHubIdentity


@receiver(user_logged_in)
def update_user(sender, request, user, **kwargs) -> None:
    """Keep the user name and the rights of a person who signed in with GitHub.

    Args:
        sender: The sender of the signal.
        request: The request.
        user: The user.
        **kwargs: More of allauth.
    """
    identity = GitHubIdentity.of(user)
    if identity is None:
        return
    admin = identity.login.lower() in settings.SITE_ADMINS
    changed = user.is_staff != admin or user.is_superuser != admin
    user.is_staff = user.is_superuser = admin
    if changed:
        user.save(update_fields=["is_staff", "is_superuser"])
