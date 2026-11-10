"""Ask the administrators by email to accept new permissions of the GitHub App."""

import logging

from allauth.account.models import EmailAddress
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from ai_pycal.github import permissions
from ai_pycal.models import Installation, Profile

log = logging.getLogger(__name__)


class PermissionNotice:
    """Compare the permissions of an installation with what the site needs; tell once."""

    def __init__(self, installation: Installation):
        """The notice for *installation*.

        Args:
            installation: The installation, with the permissions GitHub last told.
        """
        self.installation = installation

    def missing(self) -> dict[str, str]:
        """The permissions the installation lacks.

        Returns:
            The permissions and the levels needed.
        """
        return permissions.missing(self.installation.permissions or {})

    def recipients(self) -> list[str]:
        """Who gets the email: the address of the installation and its administrators.

        Returns:
            The addresses, without duplicates.
        """
        addresses = [self.installation.notify_email]
        opted_out = Profile.objects.filter(email_notifications=False).values_list(
            "user_id", flat=True
        )
        addresses += list(
            EmailAddress.objects.filter(user__in=self.installation.admins.all(), verified=True)
            .exclude(user_id__in=opted_out)
            .values_list("email", flat=True)
        )
        return sorted({address for address in addresses if address})

    def send_if_needed(self) -> bool:
        """Send the email if permissions are missing and nobody was told about them yet.

        Returns:
            True if an email was sent.
        """
        installation = self.installation
        missing = self.missing()
        described = permissions.describe(missing)
        if not missing or installation.removed:
            if installation.permissions_notified:
                installation.permissions_notified = ""
                installation.save(update_fields=["permissions_notified", "updated"])
            return False
        if installation.permissions_notified == described:
            return False
        recipients = self.recipients()
        if not recipients:
            log.warning("%s lacks %s and has no email address", installation, described)
            return False
        context = {
            "installation": installation,
            "missing": sorted(missing.items()),
            "site_name": settings.SITE_NAME,
            "site_url": settings.SITE_URL,
            "docs_url": settings.DOCS_URL.rstrip("/") + "/",
        }
        send_mail(
            render_to_string("ai_pycal/email/permissions_subject.txt", context).strip(),
            render_to_string("ai_pycal/email/permissions.txt", context),
            settings.DEFAULT_FROM_EMAIL,
            recipients,
        )
        installation.permissions_notified = described
        installation.save(update_fields=["permissions_notified", "updated"])
        return True
