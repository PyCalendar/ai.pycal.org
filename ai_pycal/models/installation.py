"""An installation of the GitHub App on an account or organization."""

from django.conf import settings
from django.db import models


class Installation(models.Model):
    """The GitHub App installed on an account or an organization of GitHub.

    The permissions are those the owners accepted. When a new version of the site
    needs more, the administrators get an email (``permissions_notified``).
    """

    github_id = models.BigIntegerField(unique=True)
    account_login = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, default="User")
    permissions = models.JSONField(default=dict, blank=True)
    # people of this site who manage the installation: they get the emails
    admins = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True)
    notify_email = models.EmailField(blank=True)
    # the missing permissions the administrators were told about, such as "statuses:write"
    permissions_notified = models.CharField(max_length=500, blank=True)
    removed = models.BooleanField(default=False)
    suspended = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["account_login"]

    def __str__(self) -> str:
        return self.account_login

    @property
    def settings_url(self) -> str:
        """The page on GitHub where the installation is configured and permissions accepted."""
        if self.account_type == "Organization":
            return (
                f"https://github.com/organizations/{self.account_login}"
                f"/settings/installations/{self.github_id}"
            )
        return f"https://github.com/settings/installations/{self.github_id}"
