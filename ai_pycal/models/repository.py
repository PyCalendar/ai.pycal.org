"""A repository whose pull requests need agreements."""

from django.conf import settings
from django.db import models

from ai_pycal.errors import by_code

from .installation import Installation


class Repository(models.Model):
    """A repository of an installation.

    It is ``active`` when an administrator added it: then its pull requests are
    checked. The error of its last reading of the configuration file is kept, so that
    the administrators see it on the page Setup.
    """

    installation = models.ForeignKey(
        Installation, on_delete=models.CASCADE, related_name="repositories"
    )
    github_id = models.BigIntegerField(unique=True)
    full_name = models.CharField(max_length=200, db_index=True)
    private = models.BooleanField(default=False)
    active = models.BooleanField(default=False)
    config_version = models.CharField(max_length=20, blank=True)
    config_commit = models.CharField(max_length=40, blank=True)
    error_code = models.CharField(max_length=100, blank=True)
    error_detail = models.TextField(blank=True)
    checked = models.DateTimeField(null=True, blank=True)
    watchers = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="watched_projects"
    )
    managed_labels = models.JSONField(default=list)
    managed_checks = models.JSONField(default=list)

    class Meta:
        ordering = ["full_name"]
        verbose_name_plural = "repositories"

    def __str__(self) -> str:
        return self.full_name

    @property
    def url(self) -> str:
        """The page of the repository on GitHub."""
        return f"https://github.com/{self.full_name}"

    @property
    def error(self):
        """The class of the error of the last reading, or None."""
        return by_code(self.error_code)
