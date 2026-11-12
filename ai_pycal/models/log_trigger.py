"""Something that happened to the site, such as a webhook or a person signing: the log."""

from django.db import models


class LogTrigger(models.Model):
    """A trigger of the log: a webhook of GitHub, or an action of a person or of the site.

    Its :class:`~ai_pycal.models.LogAction` records are what followed from it. A trigger
    that is not ``public`` is shown only in the global log of the administrators.
    """

    kind = models.CharField(max_length=50)  # such as webhook, signed, update, sign-up
    summary = models.CharField(max_length=300)
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    repository = models.ForeignKey(
        "Repository", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    pull = models.ForeignKey(
        "PullRequest", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    contributor_github_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    actor_login = models.CharField(max_length=100, blank=True)
    # the X-GitHub-Delivery of a webhook, to find it in the deliveries of the app
    delivery = models.CharField(max_length=100, blank=True)
    public = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created", "-pk"]

    def __str__(self) -> str:
        return self.summary
