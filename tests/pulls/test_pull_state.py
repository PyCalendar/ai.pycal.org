"""The state of a pull request, with its color: signed, missing, optional, merged, closed."""

import pytest

from ai_pycal.services.pull_state import PullState
from tests.conftest import REPOSITORY, pull_payload, send_webhook, sign_agreement
from tests.pulls.test_labels import versions
from tests.pulls.test_policy_choices import accept_required, open_pull

pytestmark = pytest.mark.django_db


def test_states_of_open_pull_requests(client, github, repository, alice):
    send_webhook(client, "pull_request", pull_payload(github, 1))
    pull = repository.pull_requests.get(number=1)
    assert PullState.of(pull) == "missing"
    client.force_login(alice)
    for pk in versions(repository).values():
        sign_agreement(client, pk, "alice")
    assert PullState.of(pull) == "signed"


def test_only_optional_agreements_unsigned_is_yellow(client, github, policy_project, alice):
    pull = open_pull(client, github)
    client.force_login(alice)
    accept_required(client)
    pull.refresh_from_db()
    assert PullState.of(pull) == "optional"


def test_merged_and_closed(client, github, repository):
    send_webhook(client, "pull_request", pull_payload(github, 1))
    closed = pull_payload(github, 1, action="closed")
    closed["pull_request"]["state"] = "closed"
    closed["pull_request"]["merged"] = True
    send_webhook(client, "pull_request", closed)
    pull = repository.pull_requests.get(number=1)
    assert pull.merged and PullState.of(pull) == "merged"
    pull.merged = False
    assert PullState.of(pull) == "closed"


def test_the_project_shows_open_pull_requests_and_a_switch(client, github, repository):
    send_webhook(client, "pull_request", pull_payload(github, 1))
    send_webhook(client, "pull_request", pull_payload(github, 2))
    closed = pull_payload(github, 2, action="closed")
    closed["pull_request"]["state"] = "closed"
    send_webhook(client, "pull_request", closed)
    page = client.get(f"/project/{REPOSITORY}/").content.decode()
    assert 'data-pull="1" data-pull-state="missing"' in page
    assert 'data-pull="2"' not in page and "data-all-pulls" in page
    page = client.get(f"/project/{REPOSITORY}/?pulls=all").content.decode()
    assert 'data-pull="2" data-pull-state="closed"' in page


def test_the_contributor_page_shows_the_state_not_the_choice(client, github, repository):
    send_webhook(client, "pull_request", pull_payload(github, 1))
    page = client.get("/contributor/alice/").content.decode()
    assert 'data-pull-state="missing"' in page
    assert "no policy choice" not in page and " · open · " not in page
