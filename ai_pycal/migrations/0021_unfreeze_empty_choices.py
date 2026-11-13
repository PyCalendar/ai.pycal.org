"""Pull requests first checked while their project offered no choice get its default later.

Until now the first check froze "no choice" too, so a project that added choices later never
gave its default to the pull requests checked before.
"""

from django.db import migrations


def unfreeze(apps, schema_editor):
    """Let the pull requests without a choice take the default or the preference again.

    Args:
        apps: The models of this migration.
        schema_editor: Not used.
    """
    pull_request = apps.get_model("ai_pycal", "PullRequest")
    pull_request.objects.filter(choice__isnull=True, choice_initialized=True).update(
        choice_initialized=False
    )


class Migration(migrations.Migration):
    """Unfreeze the empty choices."""

    dependencies = [("ai_pycal", "0020_agreement_translation")]

    operations = [migrations.RunPython(unfreeze, migrations.RunPython.noop)]
