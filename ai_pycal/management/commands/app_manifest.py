"""Print the manifest of the GitHub App, to create the app with the right permissions."""

import json

from django.conf import settings
from django.core.management.base import BaseCommand

from ai_pycal.github.permissions import manifest


class Command(BaseCommand):
    """``manage.py app_manifest``: see docs/how-to/github-app.rst."""

    help = "Print the manifest of the GitHub App as JSON."

    def handle(self, *args, **options):
        """Print the manifest.

        Args:
            *args: Not used.
            **options: Of Django.
        """
        self.stdout.write(json.dumps(manifest(settings.SITE_NAME, settings.SITE_URL), indent=2))
