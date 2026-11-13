"""Migration 0021: pull requests frozen without a choice get the default of the project."""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

pytestmark = pytest.mark.django_db(transaction=True)

BEFORE = [("ai_pycal", "0020_agreement_translation")]
AFTER = [("ai_pycal", "0021_unfreeze_empty_choices")]


def test_only_the_pull_requests_without_a_choice_are_unfrozen():
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    executor.migrate(BEFORE)
    try:
        old = executor.loader.project_state(BEFORE).apps
        installation = old.get_model("ai_pycal", "Installation").objects.create(
            github_id=9, account_login="PyCalendar"
        )
        repository = old.get_model("ai_pycal", "Repository").objects.create(
            installation=installation, github_id=99, full_name="PyCalendar/x", active=True
        )
        choice = old.get_model("ai_pycal", "PolicyChoice").objects.create(
            repository=repository, key="ai", name="AI", description="AI", default=True
        )
        pulls = old.get_model("ai_pycal", "PullRequest").objects
        common = {"repository": repository, "author_github_id": 1, "author_login": "a"}
        empty = pulls.create(number=1, choice_initialized=True, head_sha="a", **common)
        chosen = pulls.create(
            number=2, choice=choice, choice_initialized=True, head_sha="b", **common
        )
        executor = MigrationExecutor(connection)
        executor.migrate(AFTER)
        new = executor.loader.project_state(AFTER).apps.get_model("ai_pycal", "PullRequest")
        assert not new.objects.get(pk=empty.pk).choice_initialized
        assert new.objects.get(pk=chosen.pk).choice_initialized
    finally:
        MigrationExecutor(connection).migrate(latest)
