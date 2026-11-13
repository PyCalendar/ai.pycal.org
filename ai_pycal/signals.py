"""Who signs in with GitHub: the handle becomes the user name; SITE_ADMINS administer."""

from datetime import timedelta

from allauth.account.signals import user_logged_in, user_signed_up
from django.conf import settings
from django.dispatch import receiver
from django.utils import timezone

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
    sign_out_later(request)
    identity = GitHubIdentity.of(user)
    if identity is None:
        return
    keep_verified_addresses(user)
    admin = identity.login.lower() in settings.SITE_ADMINS
    changed = user.is_staff != admin or user.is_superuser != admin
    user.is_staff = user.is_superuser = admin
    if changed:
        user.save(update_fields=["is_staff", "is_superuser"])


def sign_out_later(request) -> None:
    """Sign the person out ``SIGN_OUT_MINUTES`` after signing in, even while they use the site.

    The time is fixed at the sign-in: using the site does not extend it.

    Args:
        request: The request of the sign-in.
    """
    session = getattr(request, "session", None)
    if session is not None:
        session.set_expiry(timezone.now() + timedelta(seconds=settings.SESSION_COOKIE_AGE))


def keep_verified_addresses(user) -> int:
    """Keep the email addresses that GitHub verified, as GitHub told them at the sign-in.

    GitHub tells them with the scope ``user:email``, read only. They identify a person and
    get the emails of the projects they watch; addresses that GitHub has not verified are
    left out, and addresses added on the site stay.

    Args:
        user: The person who signed in.

    Returns:
        How many addresses were added or verified.
    """
    from allauth.account.models import EmailAddress
    from allauth.socialaccount.models import SocialAccount

    account = SocialAccount.objects.filter(user=user, provider="github").first()
    emails = (account.extra_data.get("emails") if account else None) or []
    changed = 0
    has_primary = EmailAddress.objects.filter(user=user, primary=True).exists()
    for email in emails:
        if not (isinstance(email, dict) and email.get("verified") and email.get("email")):
            continue
        address = str(email["email"]).strip()
        if (
            EmailAddress.objects.filter(email__iexact=address, verified=True)
            .exclude(user=user)
            .exists()
        ):
            continue  # another account has it: an address identifies one person
        found = EmailAddress.objects.filter(user=user, email__iexact=address).first()
        if found is None:
            primary = bool(email.get("primary")) and not has_primary
            EmailAddress.objects.create(user=user, email=address, verified=True, primary=primary)
            has_primary = has_primary or primary
            changed += 1
        elif not found.verified:
            found.verified = True
            found.save(update_fields=["verified"])
            changed += 1
    return changed


@receiver(user_signed_up)
def record_sign_up(sender, request, user, **kwargs) -> None:
    """Record that a person signed up, in the global log of the administrators.

    Args:
        sender: The sender of the signal.
        request: The request.
        user: The new user.
        **kwargs: More of allauth.
    """
    from .actions import Trigger

    identity = GitHubIdentity.of(user)
    login = identity.login if identity else user.username
    with Trigger.start(
        "sign-up",
        f"@{login} signed up",
        contributor_github_id=identity.github_id if identity else None,
        actor_login=login,
        public=False,
    ):
        pass
