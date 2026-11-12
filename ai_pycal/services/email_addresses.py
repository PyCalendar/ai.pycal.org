"""The address to write to: one verified address per person."""

from allauth.account.models import EmailAddress

from ai_pycal.models import Profile


def notification_addresses(user_ids) -> list[str]:
    """The addresses for emails to people: one each, verified, if they want emails.

    The primary address of a person, if it is verified; otherwise their newest verified
    address, so that switching the primary address to one that is not verified yet does
    not stop the emails, nor send them to an address nobody confirmed.

    Args:
        user_ids: The people.

    Returns:
        The addresses, sorted, without people who turned emails off.
    """
    opted_out = set(
        Profile.objects.filter(email_notifications=False).values_list("user_id", flat=True)
    )
    chosen: dict[int, str] = {}
    for address in EmailAddress.objects.filter(user_id__in=list(user_ids), verified=True).order_by(
        "-primary", "-pk"
    ):
        if address.user_id not in opted_out:
            chosen.setdefault(address.user_id, address.email)
    return sorted(set(chosen.values()))


def verified_address(user) -> str:
    """The address that emails to a person go to, or "" without a verified one.

    Args:
        user: The person.

    Returns:
        The address.
    """
    found = notification_addresses([user.pk]) if user.is_authenticated else []
    return found[0] if found else ""
