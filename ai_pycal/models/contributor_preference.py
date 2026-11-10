"""Contributor defaults for a project's policy choices."""

from django.db import models


class ContributorPreference(models.Model):
    """A contributor's project default; explicit pull request choices take priority."""

    repository = models.ForeignKey("Repository", on_delete=models.CASCADE)
    github_id = models.BigIntegerField(db_index=True)
    choice = models.ForeignKey("PolicyChoice", on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["repository", "github_id"], name="one_contributor_project_default"
            )
        ]
