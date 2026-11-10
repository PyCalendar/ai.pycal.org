"""The Django app of the site."""

from django.apps import AppConfig


class AiPycalConfig(AppConfig):
    """The app: models, templates, checks and signals."""

    name = "ai_pycal"
    verbose_name = "Agreements"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        """Register the system checks and the signals."""
        from . import checks, signals  # noqa: F401
