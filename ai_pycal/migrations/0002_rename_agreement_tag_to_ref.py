"""Preserve stored agreement references under their new name."""

from django.db import migrations


class Migration(migrations.Migration):
    """Rename the field without losing existing references."""

    dependencies = [("ai_pycal", "0001_initial")]
    operations = [migrations.RenameField(model_name="requiredagreement", old_name="tag", new_name="ref")]
