"""When a new version needs more permissions, the administrators are asked by email."""

import pytest
from allauth.account.models import EmailAddress
from django.core.management import call_command

from ai_pycal.github import permissions
from ai_pycal.models import Installation
from tests.conftest import REPOSITORY, pull_payload, send_webhook

pytestmark = pytest.mark.django_db
OLD = {"metadata": "read", "contents": "read", "pull_requests": "write"}  # no statuses


@pytest.fixture
def old_installation(example, maintainer):
    example.installations[1]["permissions"] = dict(OLD)
    installation = Installation.objects.create(
        github_id=1,
        account_login="PyCalendar",
        account_type="Organization",
        permissions=dict(OLD),
    )
    maintainer.email = "maintainer@example.org"
    maintainer.save()
    EmailAddress.objects.create(user=maintainer, email=maintainer.email, verified=True)
    installation.admins.add(maintainer)
    return installation


def test_the_permissions_are_documented():
    from pathlib import Path

    text = (Path(__file__).parents[2] / "docs" / "reference" / "permissions.rst").read_text()
    for name, level in permissions.REQUIRED.items():
        assert f"``{name}``" in text and level in text
    for event in permissions.EVENTS:
        assert f"``{event}``" in text


def test_an_update_that_needs_more_permissions_sends_one_email(old_installation, mailoutbox):
    call_command("check_permissions")
    assert len(mailoutbox) == 1
    mail = mailoutbox[0]
    assert mail.to == ["maintainer@example.org"]
    assert "statuses: write" in mail.body
    assert "https://github.com/organizations/PyCalendar/settings/installations/1" in mail.body
    call_command("check_permissions")
    assert len(mailoutbox) == 1  # once


def test_accepting_the_permissions(client, example, old_installation, mailoutbox):
    call_command("check_permissions")
    example.installations[1]["permissions"] = dict(permissions.REQUIRED)
    send_webhook(
        client,
        "installation",
        {"action": "new_permissions_accepted", "installation": example.installations[1]},
    )
    old_installation.refresh_from_db()
    assert old_installation.permissions_notified == ""
    assert len(mailoutbox) == 1


def test_permission_email_uses_the_configured_documentation(old_installation, mailoutbox, settings):
    settings.DOCS_URL = "http://localhost:8123"
    call_command("check_permissions")
    assert len(mailoutbox) == 1
    assert "http://localhost:8123/reference/permissions.html" in mailoutbox[0].body
    assert "docs.sign.pycal.org" not in mailoutbox[0].body


def test_a_new_installation_with_too_few_permissions(client, example, mailoutbox, db):
    example.installations[1]["permissions"] = dict(OLD)
    send_webhook(
        client, "installation", {"action": "created", "installation": example.installations[1]}
    )
    assert mailoutbox == []  # nobody to write to yet
    assert Installation.objects.get().permissions_notified == ""


def test_the_setup_page_shows_missing_permissions(client, old_installation, maintainer):
    client.force_login(maintainer)
    page = client.get("/setup/").content.decode()
    assert "data-missing-permissions" in page and "statuses:write" in page


def test_a_missing_permission_is_an_error_with_its_documentation(client, example, old_installation):
    from ai_pycal.models import Repository
    from ai_pycal.services.repository_sync import RepositorySync

    repo = Repository.objects.create(
        installation=old_installation,
        github_id=example.repositories[REPOSITORY].id,
        full_name=REPOSITORY,
        active=True,
    )
    RepositorySync(repo).sync()
    response = send_webhook(client, "pull_request", pull_payload(example, 1))
    assert response.json()["error"] == "MissingPermissions"
    assert response.json()["documentation"].endswith("ai_pycal.errors.github.MissingPermissions")


def test_the_manifest_of_the_app(capsys):
    call_command("app_manifest")
    out = capsys.readouterr().out
    assert '"statuses": "write"' in out
    assert '"setup_url": "https://ai.example.org/setup/installed/"' in out


def test_the_permissions_are_the_minimal_set():
    """A new permission needs a reason in docs/reference/permissions.rst first."""
    assert permissions.REQUIRED == {
        "metadata": "read",
        "contents": "read",
        "pull_requests": "write",
        "statuses": "write",
    }
    from ai_pycal.github.permissions import manifest

    found = manifest("a", "https://sign.example.org")
    assert found["default_permissions"] == permissions.REQUIRED
    assert found["request_oauth_on_install"] is False


def test_the_people_who_watch_its_projects_get_the_email(old_installation, alice, mailoutbox):
    from ai_pycal.models import Repository

    EmailAddress.objects.create(user=alice, email="alice@example.org", verified=True)
    project = Repository.objects.create(
        installation=old_installation, github_id=5, full_name=REPOSITORY
    )
    project.watchers.add(alice)
    call_command("check_permissions")
    assert sorted(mailoutbox[0].to) == ["alice@example.org", "maintainer@example.org"]


def test_setup_asks_for_no_extra_address(client, repository, maintainer):
    client.force_login(maintainer)
    page = client.get("/setup/").content.decode()
    assert "Email of the installation" not in page
    assert 'type="email"' not in page
    assert client.post("/setup/1/email/", {"email": "a@example.org"}).status_code == 404
