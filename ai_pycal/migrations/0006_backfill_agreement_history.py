"""Associate existing current versions with their projects without changing signatures."""

from django.db import migrations


def backfill(apps, schema_editor):
    """Keep history visibility for agreements configured before history tracking.

    Args:
        apps: The historical migration model registry.
        schema_editor: The database schema editor.
    """
    agreement = apps.get_model("ai_pycal", "RequiredAgreement")
    version = apps.get_model("ai_pycal", "AgreementVersion")
    through = version.projects.through
    for version_id, project_id in agreement.objects.using(schema_editor.connection.alias).values_list("version_id", "repository_id").distinct():
        through.objects.using(schema_editor.connection.alias).get_or_create(agreementversion_id=version_id, repository_id=project_id)


class Migration(migrations.Migration):
    """Preserve project associations for existing agreement versions."""

    dependencies = [("ai_pycal", "0005_agreementversion_projects")]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
