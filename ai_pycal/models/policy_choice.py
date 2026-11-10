"""Policy alternatives configured by a project."""

from django.db import models


class PolicyChoice(models.Model):
    """A stable named choice whose current agreement bundle comes from YAML."""

    repository = models.ForeignKey("Repository", on_delete=models.CASCADE, related_name="choices")
    key = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    description = models.TextField()
    agreements = models.ManyToManyField("RequiredAgreement", related_name="choices")
    default = models.BooleanField(default=False)
    labels = models.JSONField(default=list)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["repository", "key"], name="unique_project_choice")
        ]
        ordering = ["position", "pk"]

    def __str__(self) -> str:
        return self.name
