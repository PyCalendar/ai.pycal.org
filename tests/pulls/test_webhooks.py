"""The webhooks: signatures, events and errors with links to the documentation."""

import json

import pytest

from ai_pycal.models import Installation, Repository
from tests.conftest import REPOSITORY, pull_payload, send_webhook

pytestmark = pytest.mark.django_db


def test_ping(client):
    assert send_webhook(client, "ping", {"zen": "x"}).json() == {"done": "pong"}


def test_unknown_events_are_ignored(client):
    assert send_webhook(client, "star", {}).json() == {"done": "ignored star"}


@pytest.mark.parametrize(
    ("secret", "error", "status"),
    [(None, "WebhookSignatureMissing", 401), ("wrong", "WebhookSignatureInvalid", 401)],
)
def test_webhooks_need_the_signature(client, secret, error, status):
    response = send_webhook(client, "ping", {}, secret=secret)
    assert response.status_code == status
    assert response.json()["error"] == error
    assert response.json()["documentation"].endswith(f"ai_pycal.errors.webhooks.{error}")


def test_without_a_secret_webhooks_are_refused(client, settings):
    settings.GITHUB_WEBHOOK_SECRET = ""
    response = send_webhook(client, "ping", {})
    assert response.status_code == 503
    assert response.json()["error"] == "WebhookSecretNotConfigured"


def test_a_body_that_is_no_json(client):
    from ai_pycal.github.webhook_signature import sign

    response = client.post(
        "/github/webhook/",
        b"no json",
        content_type="application/json",
        HTTP_X_GITHUB_EVENT="ping",
        HTTP_X_HUB_SIGNATURE_256=sign("webhook-secret", b"no json"),
    )
    assert response.json()["error"] == "WebhookPayloadInvalid"


def test_a_payload_without_what_is_needed(client, repository):
    response = send_webhook(
        client, "pull_request", {"action": "opened", "repository": {"id": repository.github_id}}
    )
    assert response.status_code == 400
    assert response.json()["error"] == "WebhookPayloadInvalid"


def test_get_is_not_allowed(client):
    assert client.get("/github/webhook/").status_code == 405


def test_installation_events(client, example, mailoutbox):
    data = dict(example.installations[1])
    assert (
        send_webhook(
            client, "installation", {"action": "created", "installation": data}
        ).status_code
        == 200
    )
    installation = Installation.objects.get(github_id=1)
    assert installation.account_login == "PyCalendar"
    assert not installation.removed
    send_webhook(client, "installation", {"action": "deleted", "installation": data})
    installation.refresh_from_db()
    assert installation.removed


def test_removed_repositories_are_no_longer_checked(client, repository):
    send_webhook(
        client,
        "installation_repositories",
        {
            "action": "removed",
            "repositories_removed": [{"id": repository.github_id}],
            "installation": {"id": 1},
        },
    )
    repository.refresh_from_db()
    assert not repository.active


def test_errors_of_github_are_shown_in_the_deliveries(client, github, repository):
    payload = pull_payload(github, 1)
    github.fail_with = 500
    response = send_webhook(client, "pull_request", payload)
    assert response.status_code == 200  # GitHub would retry nothing; the delivery shows why
    assert response.json()["error"] == "GitHubError"


def test_a_renamed_repository_keeps_its_agreements(client, github, repository):
    payload = pull_payload(github, 1)
    payload["repository"]["full_name"] = "PyCalendar/renamed"
    github.repositories["PyCalendar/renamed"] = github.repositories[REPOSITORY]
    send_webhook(client, "pull_request", payload)
    assert Repository.objects.get(pk=repository.pk).full_name == "PyCalendar/renamed"


def test_a_push_of_the_configuration_reads_it_again(client, github, repository):
    github.push(
        REPOSITORY,
        {
            ".github/agreements.yml": """
version: 1.0.0
agreements:
  cla: {name: CLA only, path: agreements/cla.md, pr: {tags: cla}}
"""
        },
    )
    payload = {
        "ref": "refs/heads/main",
        "repository": github.repositories[REPOSITORY].as_json(),
        "commits": [{"added": [], "modified": [".github/agreements.yml"], "removed": []}],
    }
    assert send_webhook(client, "push", payload).json() == {"done": "read again"}
    assert [a.name for a in repository.required_agreements.all()] == ["CLA only"]


def test_other_pushes_are_ignored(client, github, repository):
    base = {"repository": github.repositories[REPOSITORY].as_json(), "commits": []}
    assert send_webhook(client, "push", {**base, "ref": "refs/heads/feature"}).json() == {
        "done": "not the default branch"
    }
    payload = {**base, "ref": "refs/heads/main", "commits": [{"modified": ["README.md"]}]}
    assert send_webhook(client, "push", payload).json() == {"done": "nothing to read again"}


def test_a_broken_configuration_keeps_the_last_agreements(client, github, repository):
    github.push(REPOSITORY, {".github/agreements.yml": "version: 9.0.0\n"})
    response = send_webhook(client, "pull_request", pull_payload(github, 1))
    assert response.json() == {"done": "checked #1"}
    repository.refresh_from_db()
    assert repository.error_code == "ConfigVersionUnsupported"
    assert repository.required_agreements.count() == 2
    page = client.get(f"/project/{REPOSITORY}/").content.decode()
    assert 'data-error="ConfigVersionUnsupported"' in page
    assert "ai_pycal.errors.config_file.ConfigVersionUnsupported" in page


def test_json_of_errors_names_title_and_link(client):
    response = send_webhook(client, "ping", {}, secret="x")
    data = json.loads(response.content)
    assert set(data) == {"error", "title", "detail", "documentation"}
