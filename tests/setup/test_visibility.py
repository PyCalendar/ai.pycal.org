"""A repository made public or private on GitHub is shown or hidden on the site."""

import pytest
from django.core.management import call_command

from tests.conftest import REPOSITORY, send_webhook

pytestmark = pytest.mark.django_db


def make_private(repository, private=True):
    repository.private = private
    repository.save()


def test_a_repository_made_public_is_listed(client, github, repository):
    make_private(repository)
    assert REPOSITORY not in client.get("/projects/").content.decode()
    github.repositories[REPOSITORY].private = False
    payload = {"action": "publicized", "repository": github.repositories[REPOSITORY].as_json()}
    assert send_webhook(client, "repository", payload).json() == {"done": "public"}
    repository.refresh_from_db()
    assert not repository.private
    assert REPOSITORY in client.get("/projects/").content.decode()
    assert client.get(f"/project/{REPOSITORY}/").status_code == 200


def test_a_repository_made_private_is_hidden(client, github, repository):
    github.repositories[REPOSITORY].private = True
    payload = {"action": "privatized", "repository": github.repositories[REPOSITORY].as_json()}
    assert send_webhook(client, "repository", payload).json() == {"done": "private"}
    assert REPOSITORY not in client.get("/projects/").content.decode()
    assert client.get(f"/project/{REPOSITORY}/").status_code == 404


def test_a_lost_webhook_is_corrected_by_the_regular_update(client, github, repository):
    make_private(repository)  # the site missed that the repository became public
    call_command("update_repositories")
    repository.refresh_from_db()
    assert not repository.private
    assert REPOSITORY in client.get("/projects/").content.decode()


def test_every_webhook_keeps_the_visibility(client, github, repository):
    from tests.conftest import pull_payload

    make_private(repository)
    send_webhook(client, "pull_request", pull_payload(github, 1))
    repository.refresh_from_db()
    assert not repository.private
