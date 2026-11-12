"""Update every repository: a restart or an outage of the site can lose webhooks."""

from django.core.management.base import BaseCommand

from ai_pycal.actions import Trigger
from ai_pycal.errors import AgreementError
from ai_pycal.github.app import GitHubApp
from ai_pycal.models import Repository
from ai_pycal.services.repository_setup import RepositorySetup
from ai_pycal.services.repository_sync import RepositorySync


class Command(BaseCommand):
    """``manage.py update_repositories``: after the start and then regularly."""

    help = "Read the configuration, the agreements and the pull requests of every repository."

    def handle(self, *args, **options):
        """Update every active repository; errors of one do not stop the others.

        Args:
            *args: Not used.
            **options: Of Django.
        """
        if not GitHubApp.configured():
            self.stdout.write("no GitHub App configured")
            return
        updated = failed = 0
        with Trigger.start("update", "Regular update of the repositories"):
            for repository in Repository.objects.filter(active=True):
                try:
                    setup = RepositorySetup(repository)
                    RepositorySync(repository, setup.api).sync()
                    setup.check_open_pulls()
                    updated += 1
                except AgreementError as error:
                    failed += 1
                    self.stderr.write(f"{repository}: {error.code} {error}")
        self.stdout.write(f"{updated} repositories updated, {failed} failed")
