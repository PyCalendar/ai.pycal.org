"""Ask the administrators of installations without the permissions they need by email."""

from django.core.management.base import BaseCommand

from ai_pycal.errors import AgreementError
from ai_pycal.github.app import GitHubApp
from ai_pycal.models import Installation
from ai_pycal.services.permission_notice import PermissionNotice
from ai_pycal.services.webhook_handler import WebhookHandler


class Command(BaseCommand):
    """``manage.py check_permissions``: after an update and once a day."""

    help = "Read the permissions of all installations and email those that lack some."

    def handle(self, *args, **options):
        """Check every installation.

        Args:
            *args: Not used.
            **options: Of Django.
        """
        if not GitHubApp.configured():
            self.stdout.write("no GitHub App configured")
            return
        sent = 0
        for installation in Installation.objects.filter(removed=False):
            try:
                installation = WebhookHandler.store_installation(
                    GitHubApp.installation(installation.github_id)
                )
            except AgreementError as error:
                self.stderr.write(f"{installation}: {error.code} {error}")
                continue
            sent += PermissionNotice(installation).send_if_needed()
        self.stdout.write(f"{sent} emails sent")
