"""Installing the GitHub App is the only step: the webhook sets up the chosen repositories."""

import pytest

from ai_pycal.models import Installation, Repository
from tests.conftest import ALICE, REPOSITORY, send_webhook

pytestmark = pytest.mark.django_db


def installed(example, action="created", sender=ALICE, repositories=None):
    repo = example.repositories[REPOSITORY]
    return {
        "action": action,
        "installation": example.installations[1],
        "repositories": [{"id": repo.id, "full_name": REPOSITORY, "private": False}]
        if repositories is None
        else repositories,
        "sender": {"id": sender[0], "login": sender[1]},
    }


def test_installing_sets_up_the_repository_with_a_configuration(client, example):
    example.open_pull(REPOSITORY, 1, ALICE)
    response = send_webhook(client, "installation", installed(example))
    assert response.json()["done"] == "installation created: 1 set up"
    repository = Repository.objects.get(full_name=REPOSITORY)
    assert repository.active
    assert repository.required_agreements.count() == 2
    assert repository.pull_requests.filter(number=1).exists()  # the open pull request is checked
    assert "cla-missing" in example.labels[(REPOSITORY, 1)]


def test_a_repository_without_configuration_waits_for_it(client, example):
    example.push("PyCalendar/other", {"README.md": "# Other"})
    example.installation_repositories[1].append("PyCalendar/other")
    other = example.repositories["PyCalendar/other"]
    payload = installed(example, repositories=[{"id": other.id, "full_name": "PyCalendar/other"}])
    assert send_webhook(client, "installation", payload).json()["done"] == "installation created"
    repository = Repository.objects.get(full_name="PyCalendar/other")
    assert not repository.active
    example.push("PyCalendar/other", {".github/agreements.yml": "version: 2.2.0\n"})
    push = {
        "ref": "refs/heads/main",
        "repository": {"id": other.id, "full_name": "PyCalendar/other", "default_branch": "main"},
        "installation": {"id": 1},
        "commits": [{"added": [".github/agreements.yml"]}],
    }
    # the file has no agreements yet: not set up, the error is kept for Setup
    assert send_webhook(client, "push", push).json()["done"] == "not set up"
    files = {
        ".github/agreements.yml": (
            "version: 2.2.0\nagreements:\n  cla:\n    name: CLA\n    path: cla.md\n"
        ),
        "cla.md": "# CLA\n\nText.",
    }
    example.push("PyCalendar/other", files)
    assert send_webhook(client, "push", push).json()["done"] == "set up"
    repository.refresh_from_db()
    assert repository.active


def test_repositories_added_later_are_set_up(client, example):
    Installation.objects.create(github_id=1, account_login="PyCalendar")
    repo = example.repositories[REPOSITORY]
    response = send_webhook(
        client,
        "installation_repositories",
        {
            "action": "added",
            "installation": example.installations[1],
            "repositories_added": [{"id": repo.id, "full_name": REPOSITORY}],
            "repositories_removed": [],
        },
    )
    assert response.json()["done"] == "1 set up, 0 removed"
    assert Repository.objects.get(full_name=REPOSITORY).active


def test_the_installer_with_an_account_administers_and_watches(client, example, alice):
    send_webhook(client, "installation", installed(example))
    assert alice in Installation.objects.get(github_id=1).admins.all()
    assert alice in Repository.objects.get(full_name=REPOSITORY).watchers.all()


def test_a_removed_repository_stays_removed(client, example, repository):
    repository.active = False
    repository.paused = True
    repository.save()
    send_webhook(client, "installation", installed(example, action="new_permissions_accepted"))
    repository.refresh_from_db()
    assert not repository.active


def test_a_push_to_a_repository_of_no_installation_is_ignored(client, example):
    push = {
        "ref": "refs/heads/main",
        "repository": {"id": 99, "full_name": "x/y", "default_branch": "main"},
        "installation": {"id": 42},
        "commits": [{"added": [".github/agreements.yml"]}],
    }
    assert send_webhook(client, "push", push).json()["done"] == "repository not added"
    assert not Repository.objects.filter(github_id=99).exists()


def test_after_installing_no_sign_in_is_needed(client, example):
    send_webhook(client, "installation", installed(example))
    response = client.get("/setup/installed/?installation_id=1&setup_action=install")
    assert response.status_code == 200
    page = response.content.decode()
    assert "data-installed" in page
    assert f'href="/project/{REPOSITORY}/"' in page


def test_removing_and_adding_on_setup(client, example, repository, maintainer):
    client.force_login(maintainer)
    client.post(f"/setup/1/{repository.github_id}/remove/")
    repository.refresh_from_db()
    assert repository.paused and not repository.active
    client.post(f"/setup/1/{repository.github_id}/add/")
    repository.refresh_from_db()
    assert repository.active and not repository.paused
