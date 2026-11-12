"""The regular update of every repository: webhooks lost in a restart are made up for."""

import pytest
from django.core.management import call_command

from ai_pycal.models import LogTrigger
from tests.conftest import ALICE, REPOSITORY, pull_payload, send_webhook

pytestmark = pytest.mark.django_db


def test_a_lost_pull_request_webhook_is_made_up(github, repository, capsys):
    github.open_pull(REPOSITORY, 5, ALICE)  # opened while the site was down: no webhook
    call_command("update_repositories")
    pull = repository.pull_requests.get(number=5)
    assert pull.open and "cla-missing" in github.labels[(REPOSITORY, 5)]
    assert "1 repositories updated, 0 failed" in capsys.readouterr().out
    trigger = LogTrigger.objects.get(summary="Regular update of the repositories")
    assert trigger.actions.filter(kind="label-added").exists()


def test_a_lost_change_of_an_agreement_is_read(github, repository):
    old = repository.required_agreements.get(key="cla").version_id
    github.push(REPOSITORY, {"agreements/cla.md": "# CLA\n\nChanged while the site was down."})
    call_command("update_repositories")
    assert repository.required_agreements.get(key="cla").version_id != old


def test_a_pull_request_merged_while_the_site_was_down(client, github, repository):
    send_webhook(client, "pull_request", pull_payload(github, 1))
    data = github.pulls[REPOSITORY][0]
    data.update(state="closed", merged=True)  # the webhook of the merge was lost
    call_command("update_repositories")
    pull = repository.pull_requests.get(number=1)
    assert not pull.open and pull.merged and pull.state_checked


def test_older_closed_pull_requests_get_their_merge_state_once(client, github, repository):
    send_webhook(client, "pull_request", pull_payload(github, 1))
    data = github.pulls[REPOSITORY][0]
    data.update(state="closed", merged=True)
    repository.pull_requests.filter(number=1).update(open=False, merged=False)
    call_command("update_repositories")
    assert repository.pull_requests.get(number=1).merged
    requests = len(github.requests)
    call_command("update_repositories")
    asked = [r.url.path for r in github.requests[requests:]]
    assert f"/repos/{REPOSITORY}/pulls/1" not in asked  # read once


def test_an_error_of_one_repository_does_not_stop_the_others(github, repository, capsys):
    github.push(REPOSITORY, {".github/agreements.yml": "version: 9.0.0\n"})
    call_command("update_repositories")
    out = capsys.readouterr()
    assert "0 repositories updated, 1 failed" in out.out and "ConfigVersion" in out.err


def test_without_an_app_nothing_is_done(settings, capsys, db):
    settings.GITHUB_APP_ID = ""
    call_command("update_repositories")
    assert "no GitHub App configured" in capsys.readouterr().out


def test_the_container_updates_regularly():
    from pathlib import Path

    script = (Path(__file__).parents[2] / "docker" / "start-service.sh").read_text()
    assert "python manage.py update_repositories" in script
    assert "REPOSITORY_UPDATE_HOURS:-6" in script
