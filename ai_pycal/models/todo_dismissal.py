"""An optional agreement that a person removed from their todos."""

from django.conf import settings
from django.db import models

from .agreement_version import AgreementVersion


class TodoDismissal(models.Model):
    """A person does not want to be reminded of a version of an optional agreement.

    Only optional agreements can be dismissed. A new version of the agreement is a todo
    again.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    version = models.ForeignKey(AgreementVersion, on_delete=models.CASCADE)
    dismissed = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "version"], name="one_dismissal_per_version")
        ]

    def __str__(self) -> str:
        return f"{self.user} dismissed {self.version}"
