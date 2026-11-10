"""Upgrade existing signatures and references without rewriting applied migrations."""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

pytestmark = pytest.mark.django_db(transaction=True)


def test_policy_upgrade_preserves_references_signatures_and_history():
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    original = [("ai_pycal", "0001_initial")]
    executor.migrate(original)
    try:
        old = executor.loader.project_state(original).apps
        installation = old.get_model("ai_pycal", "Installation").objects.create(
            github_id=9, account_login="collective"
        )
        repository = old.get_model("ai_pycal", "Repository").objects.create(
            installation=installation, github_id=99, full_name="collective/icalendar", active=True
        )
        version = old.get_model("ai_pycal", "AgreementVersion").objects.create(
            commit="a" * 40, source="collective/policies", path="ai.md", text="AI policy"
        )
        agreement = old.get_model("ai_pycal", "RequiredAgreement").objects.create(
            repository=repository, key="ai", name="AI", tag="v1", version=version, labels=["signed"]
        )
        signature = old.get_model("ai_pycal", "Signature").objects.create(
            version=version, github_id=42, login="alice"
        )
        executor = MigrationExecutor(connection)
        executor.migrate(latest)
        new = executor.loader.project_state(latest).apps
        upgraded = new.get_model("ai_pycal", "RequiredAgreement").objects.get(pk=agreement.pk)
        assert upgraded.ref == "v1" and upgraded.mandatory
        assert upgraded.labels == ["signed"]
        assert (
            new.get_model("ai_pycal", "Signature").objects.get(pk=signature.pk).version_id
            == version.pk
        )
        assert (
            new.get_model("ai_pycal", "AgreementVersion")
            .objects.get(pk=version.pk)
            .projects.filter(pk=repository.pk)
            .exists()
        )
    finally:
        MigrationExecutor(connection).migrate(latest)
