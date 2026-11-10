"""Deliver actionable project failures without repeating unchanged emails."""

import logging

from allauth.account.models import EmailAddress
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Q

from ai_pycal.errors import ConfigFileError
from ai_pycal.models import Profile, ProjectProblem

log = logging.getLogger(__name__)


class ProjectNotices:
    """Keep project problems visible and notify opted-in verified maintainers."""

    def __init__(self, repository):
        """Select the project whose configuration or GitHub write failed.

        Args:
            repository: The affected repository.
        """
        self.repository = repository

    def record(self, error) -> None:
        """Store a problem and email it once per changed detail or recurrence.

        Args:
            error: A documented error that a maintainer can resolve.
        """
        problem, created = ProjectProblem.objects.get_or_create(
            repository=self.repository, code=error.code, defaults={"detail": str(error)}
        )
        if not created and (not problem.active or problem.detail != str(error)):
            problem.notified = False
        problem.active = True
        problem.detail = str(error)
        problem.save()
        if problem.notified:
            return
        users = self.repository.watchers.values_list("pk", flat=True)
        admins = self.repository.installation.admins.values_list("pk", flat=True)
        opted_out = Profile.objects.filter(email_notifications=False).values_list(
            "user_id", flat=True
        )
        addresses = sorted(
            set(
                EmailAddress.objects.filter(
                    Q(user_id__in=users) | Q(user_id__in=admins), verified=True
                )
                .exclude(user_id__in=opted_out)
                .values_list("email", flat=True)
            )
        )
        if not addresses:
            return
        url = f"{settings.SITE_URL}/project/{self.repository.full_name}/"
        body = (
            f"{self.repository}: {error.title}\n\n{error}\n\n{error.docs_url()}\n{url}\n\n"
            f"Manage email preferences: {settings.SITE_URL}/profile/\n"
        )
        # Keep signatures and webhook processing usable when email delivery fails.
        try:
            sent = send_mail(
                f"[{settings.SITE_NAME}] {self.repository}: {error.title}",
                body,
                settings.DEFAULT_FROM_EMAIL,
                addresses,
            )
        except Exception:
            log.exception("Could not send project problem notice for %s", self.repository)
            return
        if sent:
            problem.notified = True
            problem.save(update_fields=["notified"])

    def resolve(self, code: str) -> None:
        """Stop showing a resolved failure; a recurrence can send another email.

        Args:
            code: The error class name that was resolved.
        """
        self.repository.problems.filter(code=code, active=True).update(active=False, notified=False)

    def resolve_configuration(self) -> None:
        """Resolve configuration errors after the complete configuration was read."""
        from ai_pycal.errors import all_errors

        for code, error in all_errors().items():
            if issubclass(error, ConfigFileError) or code == "GitHubFileHistoryInvalid":
                self.resolve(code)
