"""What followed from a trigger of the log, such as a label added to a pull request."""

from django.db import models

from .log_trigger import LogTrigger


class LogAction(models.Model):
    """An action of the site, with its reason, recorded by :class:`ai_pycal.actions.Action`."""

    trigger = models.ForeignKey(LogTrigger, on_delete=models.CASCADE, related_name="actions")
    kind = models.CharField(max_length=50)  # such as label-added, status, configuration
    text = models.CharField(max_length=500)
    created = models.DateTimeField(auto_now_add=True)
    repository = models.ForeignKey(
        "Repository", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    pull = models.ForeignKey(
        "PullRequest", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    contributor_github_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    public = models.BooleanField(default=True)

    class Meta:
        ordering = ["pk"]

    def __str__(self) -> str:
        return self.text
