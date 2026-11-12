"""How a project asked for a version of an agreement: mandatory or optional."""

from django.db import models

from .agreement_version import AgreementVersion


class AgreementUse(models.Model):
    """A project asked for a version of an agreement, mandatory or optional.

    Whether an agreement is mandatory belongs to the configuration of a project at a time,
    not to the agreement: it is kept for every version a project asked for, so that the
    list of versions shows it. Each reading of the configuration updates it.
    """

    repository = models.ForeignKey(
        "Repository", on_delete=models.CASCADE, related_name="agreement_uses"
    )
    version = models.ForeignKey(AgreementVersion, on_delete=models.CASCADE, related_name="uses")
    key = models.CharField(max_length=50)
    mandatory = models.BooleanField(default=True)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["repository", "version", "key"], name="one_use_per_project_version"
            )
        ]

    def __str__(self) -> str:
        kind = "mandatory" if self.mandatory else "optional"
        return f"{self.repository} asks for {self.version} ({kind})"
