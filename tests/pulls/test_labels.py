"""Pull requests show which agreements their authors signed: labels and checks."""

import pytest

from ai_pycal.models import PullRequest, RequiredAgreement
from tests.conftest import (
    ALICE,
    BOB,
    REPOSITORY,
    pull_payload,
    send_webhook,
    shown_token,
    sign_agreement,
)

pytestmark = pytest.mark.django_db


def versions(repository):
    return {a.key: a.version_id for a in RequiredAgreement.objects.filter(repository=repository)}


def test_a_new_pull_request_asks_for_the_agreements(client, github, repository):
    response = send_webhook(client, "pull_request", pull_payload(github, 1))
    assert response.status_code == 200, response.content
    assert response.json() == {"done": "checked #1"}
    sha = github.pulls[REPOSITORY][0]["head"]["sha"]
    for key in ("ai-policy", "cla"):
        status = github.status(REPOSITORY, sha, f"ai.example.org/{key}")
        assert status["state"] == "pending"
        assert "@alice: please sign" in status["description"]
        assert status["target_url"] == f"https://ai.example.org/project/{REPOSITORY}/pulls/1/"
    # the CLA is not signed yet: pr.unsigned-labels of the configuration
    assert github.labels.get((REPOSITORY, 1), []) == ["cla-missing"]


def test_signing_labels_the_open_pull_requests(client, github, repository, alice):
    send_webhook(client, "pull_request", pull_payload(github, 1))
    send_webhook(client, "pull_request", pull_payload(github, 2, author=BOB))
    client.force_login(alice)
    ids = versions(repository)

    response = sign_agreement(client, ids["ai-policy"], "alice")
    assert response.status_code == 302
    assert sorted(github.labels[(REPOSITORY, 1)]) == ["ai-policy-accepted", "cla-missing"]
    assert github.labels[(REPOSITORY, 2)] == ["cla-missing"]  # bob did not sign
    sha = github.pulls[REPOSITORY][0]["head"]["sha"]
    assert github.status(REPOSITORY, sha, "ai.example.org/ai-policy")["state"] == "success"
    assert github.status(REPOSITORY, sha, "ai.example.org/cla")["state"] == "pending"
    assert not PullRequest.objects.get(number=1).all_signed

    sign_agreement(client, ids["cla"], "@Alice")
    assert sorted(github.labels[(REPOSITORY, 1)]) == ["ai-policy-accepted", "cla-signed"]
    assert PullRequest.objects.get(number=1).all_signed


def test_a_pull_request_of_someone_who_signed_is_labelled_at_once(
    client, github, repository, alice
):
    client.force_login(alice)
    send_webhook(client, "pull_request", pull_payload(github, 1))
    for pk in versions(repository).values():
        sign_agreement(client, pk, "alice")
    send_webhook(client, "pull_request", pull_payload(github, 3))
    assert set(github.labels[(REPOSITORY, 3)]) == {"ai-policy-accepted", "cla-signed"}


def test_a_label_of_several_agreements_needs_all_of_them(client, github, repository, alice):
    github.push(
        REPOSITORY,
        {
            ".github/agreements.yml": """
version: 1.0.0
agreements:
  ai-policy: {name: AI, path: agreements/ai-policy.md, pr: {tags: [ai, all]}}
  cla: {name: CLA, path: agreements/cla.md, pr: {tags: [cla, all]}}
"""
        },
    )
    send_webhook(client, "pull_request", pull_payload(github, 1))
    client.force_login(alice)
    sign_agreement(client, versions(repository)["ai-policy"], "alice")
    assert github.labels[(REPOSITORY, 1)] == ["ai"]
    sign_agreement(client, versions(repository)["cla"], "alice")
    assert sorted(github.labels[(REPOSITORY, 1)]) == ["ai", "all", "cla"]


def test_the_page_of_a_pull_request_shows_the_agreements(client, github, repository, alice):
    send_webhook(client, "pull_request", pull_payload(github, 1))
    page = client.get(f"/repository/{REPOSITORY}/pull/1/").content.decode()
    assert 'data-agreement="ai-policy"' in page and "Unsigned" in page
    client.force_login(alice)
    sign_agreement(client, versions(repository)["ai-policy"], "alice")
    page = client.get(f"/repository/{REPOSITORY}/pull/1/").content.decode()
    assert page.count('data-state="missing"') == 1


def test_an_unknown_pull_request_has_its_error(client, repository):
    response = client.get(f"/repository/{REPOSITORY}/pull/99/")
    assert response.status_code == 404
    assert b'data-error="PullRequestNotFound"' in response.content
    assert b"reference/errors.html#ai_pycal.errors.signing.PullRequestNotFound" in response.content


def test_signing_returns_to_the_pull_request(client, github, repository, alice):
    send_webhook(client, "pull_request", pull_payload(github, 1))
    client.force_login(alice)
    target = f"/repository/{REPOSITORY}/pull/1/"
    response = sign_agreement(client, versions(repository)["cla"], "alice", next=target)
    assert response["Location"] == target
    response = sign_agreement(
        client, versions(repository)["ai-policy"], "alice", next="//evil.example"
    )
    assert response["Location"] == f"/agreements/{versions(repository)['ai-policy']}/"


def test_a_closed_pull_request_is_not_checked(client, github, repository):
    payload = pull_payload(github, 1, action="closed")
    payload["pull_request"]["state"] = "closed"
    assert send_webhook(client, "pull_request", payload).json() == {"done": "pull request closed"}
    assert not PullRequest.objects.get(number=1).open
    assert github.statuses == []


def test_pull_requests_of_repositories_not_added_are_ignored(client, example):
    response = send_webhook(client, "pull_request", pull_payload(example, 1))
    assert response.json() == {"done": "repository not added"}


def test_signing_twice_is_noticed(client, github, repository, alice):
    client.force_login(alice)
    pk = versions(repository)["cla"]
    token = shown_token(client, pk)
    sign_agreement(client, pk, "alice", token=token)
    response = sign_agreement(client, pk, "alice", token=token)
    assert response.status_code == 302
    assert "already signed" in client.get(response["Location"]).content.decode()


def test_the_check_of_open_pull_requests_when_the_repository_is_added(client, example, maintainer):
    example.open_pull(REPOSITORY, 5, ALICE)
    client.force_login(maintainer)
    repo_id = example.repositories[REPOSITORY].id
    response = client.post(f"/setup/1/{repo_id}/add/")
    assert response.status_code == 302
    sha = example.pulls[REPOSITORY][0]["head"]["sha"]
    assert example.status(REPOSITORY, sha, "ai.example.org/cla")["state"] == "pending"


def test_an_unsigned_label_shared_by_agreements_stays_until_all_are_signed():
    from types import SimpleNamespace

    from ai_pycal.services.pull_request_check import PullRequestCheck

    def state(signed, labels=(), unsigned=()):
        agreement = SimpleNamespace(labels=list(labels), unsigned_labels=list(unsigned))
        return SimpleNamespace(agreement=agreement, signed=signed, required=True)

    states = [state(True, ["a"], ["missing"]), state(False, ["b"], ["missing"])]
    add, remove = PullRequestCheck.labels(states)
    assert "missing" in add and "missing" not in remove
    assert "a" in add and "b" in remove
    add, remove = PullRequestCheck.labels([state(True, ["a"], ["missing"])])
    assert add == {"a"} and remove == {"missing"}


def test_a_reopened_pull_request_gets_the_labels_of_the_changed_agreement(
    client, github, repository, alice
):
    send_webhook(client, "pull_request", pull_payload(github, 1))
    client.force_login(alice)
    sign_agreement(client, versions(repository)["cla"], "alice")
    assert "cla-signed" in github.labels[(REPOSITORY, 1)]
    send_webhook(client, "pull_request", pull_payload(github, 1, action="closed"))
    github.push(REPOSITORY, {"agreements/cla.md": "# CLA\n\nChanged while closed."})
    send_webhook(client, "pull_request", pull_payload(github, 1, action="reopened"))
    labels = github.labels[(REPOSITORY, 1)]
    assert "cla-signed" not in labels and "cla-missing" in labels
