"""A translation of an agreement, for reading; the original is what people sign."""

from django.db import models

from .agreement_version import AgreementVersion


class AgreementTranslation(models.Model):
    """The file ``<name>.<language>.md`` next to the file of an agreement.

    It is read with the agreement, at the same commit of its reference, and shown to people
    who use the site in its language. Signing always signs the original version.
    """

    version = models.ForeignKey(
        AgreementVersion, on_delete=models.CASCADE, related_name="translations"
    )
    language = models.CharField(max_length=10)
    path = models.CharField(max_length=500)
    commit = models.CharField(max_length=40)  # the commit of the reference it was read at
    title = models.CharField(max_length=300, blank=True)
    text = models.TextField()
    read = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["version", "language"], name="one_translation_per_language"
            )
        ]
        ordering = ["version", "language"]

    def __str__(self) -> str:
        return f"{self.path} ({self.language})"
