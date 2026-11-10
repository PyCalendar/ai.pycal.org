"""Prepare the site at every start: the database and the domain."""

from urllib.parse import urlparse

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.core.management.base import BaseCommand


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
