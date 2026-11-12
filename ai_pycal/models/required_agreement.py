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
    # seconds between opening and signing it, at least; null: the site's SIGN_MIN_SECONDS
    sign_min_seconds = models.FloatField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["repository", "key"], name="one_agreement_per_key")
        ]
        ordering = ["repository", "-mandatory", "position"]  # mandatory first

    @property
    def reading_seconds(self) -> int | None:
        """The reading time of the configuration in whole seconds, None if it sets none."""
        return None if self.sign_min_seconds is None else round(self.sign_min_seconds)

    @property
    def title(self) -> str:
        """The name of the agreement for people: the title of its file, else its name."""
        return self.version.title or self.name

    def __str__(self) -> str:
        return f"{self.repository}: {self.key}"
