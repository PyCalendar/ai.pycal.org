"""Ask the administrators of installations without the permissions they need by email."""

from django.core.management.base import BaseCommand

from ai_pycal.actions import Trigger
from ai_pycal.errors import AgreementError
from ai_pycal.github import permissions
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
        with Trigger.start(
            "permissions", "Check of the permissions of the installations", public=False
        ):
            sent = self.check_all()
        self.stdout.write(f"{sent} emails sent")
        self.check_events()

    def check_events(self) -> None:
        """Print the events that the app does not receive, with the page to add them."""
        try:
            app = GitHubApp.describe()
        except AgreementError as error:
            self.stderr.write(f"the events of the app could not be read: {error.code}")
            return
        missing = permissions.missing_events(app.get("events") or [])
        if missing:
            self.stdout.write(
                f"the app does not receive the events {', '.join(missing)}: "
                f"tick them on {GitHubApp.settings_url(app)}"
            )

    def check_all(self) -> int:
        """Check every installation that is not removed.

        Returns:
            How many emails were sent.
        """
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
        return sent
