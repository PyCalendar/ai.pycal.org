"""Prepare the site at every start: the database, the domain and the setup code of the app."""

from urllib.parse import urlparse

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.core.management.base import BaseCommand

from ai_pycal.services.app_registration import AppRegistration


class Command(BaseCommand):
    """``manage.py prepare``: migrate and set the domain of ``SITE_URL``."""

    help = "Migrate the database and set the domain of the site."

    def handle(self, *args, **options):
        """Prepare the site.

        Args:
            *args: Not used.
            **options: Of Django.
        """
        call_command("migrate", interactive=False, verbosity=0)
        domain = urlparse(settings.SITE_URL).netloc or "localhost"
        Site.objects.update_or_create(
            pk=settings.SITE_ID, defaults={"domain": domain, "name": settings.SITE_NAME}
        )
        self.stdout.write(f"prepared {domain}")
        obstacle = None if AppRegistration.source() else AppRegistration.obstacle()
        if obstacle:
            self.stdout.write(
                f"This site has no GitHub App and cannot register one: {obstacle.title}: "
                f"{obstacle.detail} ({obstacle.docs_url()})"
            )
        elif not AppRegistration.source():
            self.stdout.write(
                "This site has no GitHub App. Register it on "
                f"{settings.SITE_URL}/setup/github-app/ with the setup code "
                f"{AppRegistration.setup_code()}"
            )
