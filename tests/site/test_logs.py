"""The logs: every trigger and the actions that followed, for each page and for admins."""

import pytest

from ai_pycal.models import LogAction, LogTrigger
from tests.conftest import (
    REPOSITORY,
    pull_payload,
    send_webhook,
    sign_agreement,
)
from tests.pulls.test_labels import versions

pytestmark = pytest.mark.django_db


def triggers(page: str) -> list[str]:
    return [part.split("</span>")[0] for part in page.split('class="log-summary">')[1:]]


def test_a_pull_request_log_shows_why_labels_changed(client, github, repository, alice):
    send_webhook(client, "pull_request", pull_payload(github, 1))
    client.force_login(alice)
    sign_agreement(client, versions(repository)["cla"], "alice")
    page = client.get(f"/logs/{REPOSITORY}/pulls/1/").content.decode()
    assert "@alice signs an agreement" in triggers(page)
    assert any(t.startswith("Pull request #1 opened") for t in triggers(page))
    assert "Label cla-signed added to #1: Contributor License Agreement (example) is signed" in page
    assert (
        "Label cla-missing removed from #1: Contributor License Agreement (example) is signed"
        in page
    )
    assert "<details open" not in page  # only the triggers, until one is opened


def test_a_configuration_update_shows_its_actions(client, github, repository):
    send_webhook(client, "pull_request", pull_payload(github, 1))
    github.push(REPOSITORY, {"agreements/cla.md": "# CLA\n\nChanged."})
    send_webhook(
        client,
        "push",
        {
            "ref": "refs/heads/main",
            "repository": {
                "id": repository.github_id,
                "full_name": REPOSITORY,
                "default_branch": "main",
            },
            "commits": [{"modified": [".github/agreements.yml", "agreements/cla.md"]}],
        },
    )
    page = client.get(f"/logs/{REPOSITORY}/").content.decode()
    assert "Repository configuration updated" in triggers(page)
    update = page.split("Repository configuration updated")[1].split("</details>")[0]
    assert "Configuration 2.1.0 read: 2 agreements" in update
    assert "New version of Contributor License Agreement (example)" in update
    assert "Check ai.example.org/cla of #1: pending" in update


def test_the_page_of_a_pull_request_shows_only_its_actions(client, github, repository):
    send_webhook(client, "pull_request", pull_payload(github, 1))
    send_webhook(client, "pull_request", pull_payload(github, 2))
    page = client.get(f"/logs/{REPOSITORY}/pulls/1/").content.decode()
    assert "#2" not in page.split("<main")[1].split("</h1>")[1]


def test_triggers_without_actions_are_gray(client, github, repository, settings, maintainer):
    send_webhook(client, "ping", {"zen": "Keep it logically awesome."})
    settings.SITE_ADMINS = ["maintainer"]
    client.force_login(maintainer)
    page = client.get("/logs/all/").content.decode()
    ping = page.split('data-trigger="webhook"')[-1]
    assert "Ping of GitHub" in page
    assert 'class="log-trigger log-empty"' in page and "no actions" in ping


def test_the_global_log_is_for_site_admins(client, repository, alice, maintainer, settings):
    assert client.get("/logs/all/").status_code == 403
    client.force_login(alice)
    assert client.get("/logs/all/").status_code == 403
    settings.SITE_ADMINS = ["maintainer"]
    client.force_login(maintainer)
    page = client.get("/logs/all/").content.decode()
    assert "Global log" in page
    menu = client.get("/").content.decode().split('<details class="account-menu">')[1]
    assert 'href="/logs/all/">Global log' in menu.split("</details>")[0]


def test_sensitive_actions_are_only_in_the_global_log(client, repository, maintainer, settings):
    with _sensitive(repository):
        pass
    page = client.get(f"/logs/{REPOSITORY}/").content.decode()
    assert "Email to 1 addresses" not in page
    settings.SITE_ADMINS = ["maintainer"]
    client.force_login(maintainer)
    assert "Email to 1 addresses" in client.get("/logs/all/").content.decode()


def _sensitive(repository):
    from contextlib import contextmanager

    from ai_pycal.actions import EmailSent, Trigger

    @contextmanager
    def run():
        with Trigger.start("permissions", "Check of permissions", public=False):
            EmailSent("New permissions", "text", ["a@example.org"], repository=repository).run()
        yield

    return run()


def test_admins_can_open_a_trigger_in_the_global_log(
    client, github, repository, maintainer, settings
):
    send_webhook(client, "pull_request", pull_payload(github, 1))
    settings.SITE_ADMINS = ["maintainer"]
    client.force_login(maintainer)
    page = client.get(f"/logs/{REPOSITORY}/").content.decode()
    trigger = LogTrigger.objects.filter(kind="webhook").first()
    link = f'href="/logs/all/?trigger={trigger.pk}#trigger-{trigger.pk}"'
    assert link in page
    opened = client.get(f"/logs/all/?trigger={trigger.pk}").content.decode()
    assert f'id="trigger-{trigger.pk}"' in opened and "<details open" in opened


def test_every_webhook_is_recorded_also_refused_ones(client):
    response = client.post(
        "/github/webhook/",
        b"{}",
        content_type="application/json",
        HTTP_X_GITHUB_EVENT="push",
        HTTP_X_GITHUB_DELIVERY="abc-1",
    )
    assert response.status_code == 401
    trigger = LogTrigger.objects.get(delivery="abc-1")
    assert trigger.summary.startswith("Refused webhook push") and not trigger.public


def test_a_sign_up_is_recorded(rf, alice):
    from allauth.account.signals import user_signed_up

    user_signed_up.send(sender=None, request=rf.get("/"), user=alice)
    trigger = LogTrigger.objects.get(kind="sign-up")
    assert trigger.summary == "@alice signed up" and not trigger.public


def test_actions_outside_a_trigger_are_kept(repository):
    from ai_pycal.actions import ConfigurationRead

    ConfigurationRead(repository, "2.1.0", 2).run()
    action = LogAction.objects.order_by("-pk").first()
    assert action.trigger.kind == "background" and not action.trigger.public


def test_contributor_log(client, github, repository, alice):
    send_webhook(client, "pull_request", pull_payload(github, 1))
    client.force_login(alice)
    sign_agreement(client, versions(repository)["cla"], "alice")
    page = client.get("/logs/contributor/alice/").content.decode()
    assert "@alice signed Contributor License Agreement (example)" in page
    assert 'href="/logs/contributor/alice/"' in client.get("/contributor/alice/").content.decode()


def test_the_path_of_a_log_navigates_the_logs_and_back(client, github, repository):
    send_webhook(client, "pull_request", pull_payload(github, 1))
    page = client.get(f"/logs/{REPOSITORY}/pulls/1/").content.decode()
    title = page.split('<h1 class="crumbs-path">')[1].split("</h1>")[0]
    assert 'href="/logs/PyCalendar/"' in title
    assert f'href="/logs/{REPOSITORY}/"' in title
    assert f'href="/logs/{REPOSITORY}/pulls/1/"' in title
    assert f'href="/project/{REPOSITORY}/pulls/1/">← Back to the pull request' in page
    owner = client.get("/logs/PyCalendar/").content.decode()
    assert "Pull request #1 opened" in owner


def test_handles_in_the_log_link_to_the_people(client, github, repository, alice):
    send_webhook(client, "pull_request", pull_payload(github, 1))
    client.force_login(alice)
    sign_agreement(client, versions(repository)["cla"], "alice")
    page = client.get(f"/logs/{REPOSITORY}/").content.decode()
    assert '<a href="/contributor/alice/">@alice</a>' in page


@pytest.mark.parametrize(
    ("page", "log"),
    [
        (f"/project/{REPOSITORY}/pulls/1/", f"/logs/{REPOSITORY}/pulls/1/"),
        (f"/project/{REPOSITORY}/", f"/logs/{REPOSITORY}/"),
        (f"/project/{REPOSITORY}/status/", f"/logs/{REPOSITORY}/"),
        ("/contributor/alice/", "/logs/contributor/alice/"),
    ],
)
def test_the_log_is_the_icon_next_to_the_title(client, github, repository, page, log):
    send_webhook(client, "pull_request", pull_payload(github, 1))
    html = client.get(page).content.decode()
    title = html.split("<main")[1].split("</h1>", 1)[1].split("</div>")[0]  # after the title
    assert f'class="log-link" data-log href="{log}"' in title
    assert html.count(f'href="{log}"') == 1  # no other link to the log, such as a text
    assert "<p>" not in html.split("<title>")[1].split("</title>")[0]
