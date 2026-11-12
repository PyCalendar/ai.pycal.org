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
        unknown = self.unknown_admins()
        if unknown:
            self.stdout.write(
                "SITE_ADMINS without an account on this site (a typo, or they never signed "
                f"in): {', '.join(unknown)}"
            )
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

    @staticmethod
    def unknown_admins() -> list[str]:
        """The handles of ``SITE_ADMINS`` that no account of the site has.

        Returns:
            The handles, such as a misspelled one; they get admin rights when they sign in.
        """
        from allauth.socialaccount.models import SocialAccount

        known = {
            str(account.extra_data.get("login", "")).lower()
            for account in SocialAccount.objects.filter(provider="github")
        }
        return [login for login in settings.SITE_ADMINS if login not in known]
