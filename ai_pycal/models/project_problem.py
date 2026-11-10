"""Persistent project problems shown to maintainers until resolved."""

from django.db import models

from ai_pycal.errors import by_code


class ProjectProblem(models.Model):
    """One actionable cause per project, with email deduplication and resolution."""

    repository = models.ForeignKey("Repository", on_delete=models.CASCADE, related_name="problems")
    code = models.CharField(max_length=100)
    detail = models.TextField()
    active = models.BooleanField(default=True)
    notified = models.BooleanField(default=False)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["repository", "code"], name="one_problem_per_project_cause"
            )
        ]
        ordering = ["-updated"]

    @property
    def error(self):
        """The documented error type explaining how to resolve this problem."""
        return by_code(self.code)
