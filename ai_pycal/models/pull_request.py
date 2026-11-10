"""A pull request of a repository that needs agreements."""

from django.db import models

from .repository import Repository


class PullRequest(models.Model):
    """A pull request, as GitHub last told about it.

    The site checks open pull requests again when their author signs an agreement.
    """

    repository = models.ForeignKey(
        Repository, on_delete=models.CASCADE, related_name="pull_requests"
    )
    number = models.PositiveIntegerField()
    title = models.CharField(max_length=500, blank=True)
    author_github_id = models.BigIntegerField(db_index=True)
    author_login = models.CharField(max_length=100)
    head_sha = models.CharField(max_length=40)
    open = models.BooleanField(default=True)
    all_signed = models.BooleanField(default=False)
    choice = models.ForeignKey("PolicyChoice", null=True, blank=True, on_delete=models.SET_NULL)
    choice_initialized = models.BooleanField(default=False)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["repository", "number"], name="one_pull_per_number")
        ]
        ordering = ["-updated"]

    def __str__(self) -> str:
        return f"{self.repository}#{self.number}"

    @property
    def url(self) -> str:
        """The pull request on GitHub."""
        return f"{self.repository.url}/pull/{self.number}"
