"""The repository event: a new default branch, a renamed repository; the events of the app."""

import pytest
from django.core.management import call_command

from ai_pycal.models import LogTrigger
from tests.conftest import REPOSITORY, pull_payload, send_webhook

pytestmark = pytest.mark.django_db


def repository_payload(stored, action, data=None, **extra):
    found = {"id": stored.github_id, "full_name": REPOSITORY, "default_branch": "main"}
    found.update(data or {})
    return {"action": action, "repository": found, **extra}


def test_a_new_default_branch_reads_the_configuration_again(client, github, repository):
    send_webhook(client, "pull_request", pull_payload(github, 1))
    github.push(REPOSITORY, {"agreements/cla.md": "# CLA\n\nOn the new branch."})
    old = repository.required_agreements.get(key="cla").version_id
    send_webhook(
        client,
        "repository",
        repository_payload(repository, "edited", changes={"default_branch": {"from": "master"}}),
    )
    assert repository.required_agreements.get(key="cla").version_id != old
    trigger = LogTrigger.objects.filter(kind="webhook").order_by("-pk").first()
    assert trigger.summary == "Default branch changed to main"
    assert trigger.actions.filter(kind="configuration").exists()


def test_a_renamed_repository_keeps_its_records(client, repository):
    send_webhook(
        client,
        "repository",
        repository_payload(repository, "renamed", {"full_name": "PyCalendar/renamed"}),
    )
    repository.refresh_from_db()
    assert repository.full_name == "PyCalendar/renamed"


def test_the_app_subscribes_to_the_repository_event():
    from ai_pycal.github.permissions import EVENTS, manifest

    assert "repository" in EVENTS
    assert "repository" in manifest("a", "https://ai.example.org")["default_events"]


def test_site_admins_see_missing_events(client, github, repository, maintainer, settings):
    github.app_events = ["pull_request", "push"]
    client.force_login(maintainer)
    assert "data-missing-events" not in client.get("/setup/").content.decode()
    settings.SITE_ADMINS = ["maintainer"]
    page = client.get("/setup/").content.decode()
    message = page.split("data-missing-events")[1].split("</div>")[0]
    assert "<code>repository</code>" in message
    assert (
        "https://github.com/organizations/PyCalendar/settings/apps/ai-pycal-test/permissions"
        in message
    )
    github.app_events.append("repository")
    assert "data-missing-events" not in client.get("/setup/").content.decode()


def test_the_command_prints_missing_events(github, repository, capsys):
    github.app_events = ["push"]
    call_command("check_permissions")
    out = capsys.readouterr().out
    assert "the app does not receive the events pull_request, repository" in out
