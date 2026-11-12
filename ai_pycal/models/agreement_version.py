"""The text of an agreement at a commit."""

from django.db import models


class AgreementVersion(models.Model):
    """The file of an agreement at a commit: what people sign.

    The commit is the last edit of the file within the configured reference.
    It is identified by source repository, commit and path: repositories that ask for the same
    file at the same commit ask for the same agreement, and a signature counts for all
    of them. A changed file is a new commit and needs a new signature.
    """

    commit = models.CharField(max_length=40)
    path = models.CharField(max_length=500)
    # the source repository, owner/name
    source = models.CharField(max_length=200)
    text = models.TextField()
    fetched = models.DateTimeField(auto_now_add=True)
    # the time of the commit: people see it as the version; None if not known yet
    committed = models.DateTimeField(null=True, blank=True)
    projects = models.ManyToManyField("Repository", related_name="agreement_history", blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source", "commit", "path"], name="one_version_per_source_commit_path"
            )
        ]
        ordering = ["-fetched"]

    def __str__(self) -> str:
        return f"{self.source}/{self.path}@{self.commit[:7]}"

    @property
    def short_commit(self) -> str:
        """The first seven characters of the commit, as GitHub shows it."""
        return self.commit[:7]

    @property
    def url(self) -> str:
        """The file on GitHub at its commit."""
        return f"https://github.com/{self.source}/blob/{self.commit}/{self.path}"
