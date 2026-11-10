"""A signature of an agreement by a person on GitHub."""

from django.conf import settings
from django.db import models

from .agreement_version import AgreementVersion


class Signature(models.Model):
    """A person accepted a version of an agreement.

    People are identified by the id GitHub gives their account, which stays when
    they change their handle. ``login`` is the handle at the time of signing.
    """

    version = models.ForeignKey(
        AgreementVersion, on_delete=models.PROTECT, related_name="signatures"
    )
    github_id = models.BigIntegerField(db_index=True)
    login = models.CharField(max_length=100)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    signed = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["version", "github_id"], name="sign_once")]
        ordering = ["-signed"]

    def __str__(self) -> str:
        return f"@{self.login} signed {self.version}"
