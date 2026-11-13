"""Show the setup code that allows registering the GitHub App on the site."""

from django.conf import settings
from django.core.management.base import BaseCommand

from ai_pycal.services.app_registration import AppRegistration


class Command(BaseCommand):
    """``manage.py github_app_setup_code``: the code for the page *Register GitHub App*."""

    help = "Show the setup code for registering the GitHub App on the site."

    def handle(self, *args, **options):
        """Print the code, or that the site has an app.

        Args:
            *args: Not used.
            **options: Of Django.
        """
        source = AppRegistration.source()
        if source and not settings.SIGN_IN_WITH_OAUTH_APP:
            # the OAuth app for signing in is entered with the code
            self.stdout.write(AppRegistration.setup_code())
            return
        if source:
            self.stdout.write(
                f"The site has a GitHub App (from the {source}) and an OAuth app; "
                "no code is needed."
            )
            return
        obstacle = AppRegistration.obstacle()
        if obstacle:
            self.stdout.write(
                f"The site cannot register its GitHub App: {obstacle.title}: {obstacle}"
            )
            return
        self.stdout.write(AppRegistration.setup_code())
