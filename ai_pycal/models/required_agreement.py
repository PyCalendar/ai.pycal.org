"""An agreement that a repository asks for."""

from django.db import models

from .agreement_version import AgreementVersion
from .repository import Repository


class RequiredAgreement(models.Model):
    """An agreement of the configuration file of a repository, as last read.

    ``key`` is the identifier of the agreement in the file; ``labels`` are set on the
    pull requests of people who signed ``version``.
    """

    repository = models.ForeignKey(
        Repository, on_delete=models.CASCADE, related_name="required_agreements"
    )
    key = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    ref = models.CharField(max_length=250, blank=True)
    description = models.TextField(blank=True)
    mandatory = models.BooleanField(default=True)
    version = models.ForeignKey(
        AgreementVersion, on_delete=models.PROTECT, related_name="required_by"
    )
    labels = models.JSONField(default=list)
    # the labels of a pull request while this agreement is required and not signed
    unsigned_labels = models.JSONField(default=list, blank=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["repository", "key"], name="one_agreement_per_key")
        ]
        ordering = ["repository", "-mandatory", "position"]  # mandatory first

    def __str__(self) -> str:
        return f"{self.repository}: {self.key}"
