"""Ask the administrators by email to accept new permissions of the GitHub App."""

import logging

from django.conf import settings
from django.template.loader import render_to_string

from ai_pycal.actions import EmailSent
from ai_pycal.github import permissions
from ai_pycal.models import Installation
from ai_pycal.services.email_addresses import notification_addresses

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
        """Who gets the email: the administrators and the people who watch its projects.

        Each person gets it at the address they have on the site (no extra address).

        Returns:
            The addresses, without duplicates.
        """
        people = set(self.installation.admins.values_list("pk", flat=True))
        people |= set(
            self.installation.repositories.filter(watchers__isnull=False).values_list(
                "watchers", flat=True
            )
        )
        return sorted(set(notification_addresses(people)))

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
        EmailSent(
            render_to_string("ai_pycal/email/permissions_subject.txt", context).strip(),
            render_to_string("ai_pycal/email/permissions.txt", context),
            recipients,
        ).run()
        installation.permissions_notified = described
        installation.save(update_fields=["permissions_notified", "updated"])
        return True
