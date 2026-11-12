"""The signing flow of a pull request: sign in, the agreements one by one, then back."""

import re

import pytest

from ai_pycal.models import Signature
from tests.conftest import REPOSITORY, pull_payload, send_webhook
from tests.pulls.test_policy_choices import flow_step, open_pull, page_url

pytestmark = pytest.mark.django_db
FLOW = f"/project/{REPOSITORY}/pulls/1/sign/"


def sign_step(client, version, token, handle="alice"):
    return client.post(
        FLOW,
        {"version": version, "shown": token, "accept": "yes", "handle": handle, "action": "sign"},
    )


def links_in_the_header_and_footer(page: str) -> list[str]:
    header = page.split('<header class="nav">')[1].split("</header>")[0]
    footer = page.split('<footer class="footer">')[1].split("</footer>")[0]
    return re.findall(r"<a [^>]*>", header) + re.findall(r"<a [^>]*>", footer)


def test_visitors_sign_in_first_and_come_back(client, github, repository):
    send_webhook(client, "pull_request", pull_payload(github, 1))
    response = client.get(FLOW)
    assert response.status_code == 302
    assert response["Location"] == f"/accounts/login/?next={FLOW}"


def test_the_sign_in_into_the_flow_has_no_links_away(client, github, repository):
    page = client.get(f"/accounts/login/?next={FLOW}").content.decode()
    links = links_in_the_header_and_footer(page)
    assert links == ['<a href="/about/" target="_blank" rel="noopener">']


def test_the_flow_has_no_links_away_and_shows_the_progress(client, github, repository, alice):
    send_webhook(client, "pull_request", pull_payload(github, 1))
    client.force_login(alice)
    page = client.get(FLOW).content.decode()
    assert links_in_the_header_and_footer(page) == [
        '<a href="/about/" target="_blank" rel="noopener">'
    ]
    assert "account-menu" not in page and "Agreement 1 of 2" in page
    assert '<progress value="1" max="2">' in page
    assert 'name="handle"' in page and "pattern=" in page


def test_signing_all_agreements_ends_with_two_ways_back(client, github, repository, alice):
    send_webhook(client, "pull_request", pull_payload(github, 1))
    client.force_login(alice)
    for position in (1, 2):
        version, token, page = flow_step(client)
        assert f"Agreement {position} of 2" in page
        assert ("Sign and continue" in page) == (position == 1)
        assert sign_step(client, version, token).status_code == 302
    page = client.get(FLOW).content.decode()
    done = page.split('data-step="done"')[1]
    assert f'href="https://github.com/{REPOSITORY}/pull/1"' in done
    assert f'href="/project/{REPOSITORY}/pulls/1/"' in done
    assert "All done" in done
    assert Signature.objects.count() == 2
    assert "cla-signed" in github.labels[(REPOSITORY, 1)]


def test_a_wrong_handle_stays_in_the_flow(client, github, repository, alice):
    send_webhook(client, "pull_request", pull_payload(github, 1))
    client.force_login(alice)
    version, token, _ = flow_step(client)
    response = sign_step(client, version, token, handle="bob")
    assert response.status_code == 400
    page = response.content.decode()
    assert 'data-error="HandleMismatch"' in page and 'data-step="agreement"' in page
    assert links_in_the_header_and_footer(page) == [
        '<a href="/about/" target="_blank" rel="noopener">'
    ]
    assert not Signature.objects.exists()


def test_required_agreements_can_not_be_skipped(client, github, repository, alice):
    send_webhook(client, "pull_request", pull_payload(github, 1))
    client.force_login(alice)
    version, _, page = flow_step(client)
    assert "data-skip" not in page
    client.post(FLOW, {"version": version, "action": "skip"})
    assert flow_step(client)[0] == version  # still the same step


def test_optional_agreements_can_be_skipped(client, github, policy_project, alice):
    open_pull(client, github)
    client.force_login(alice)
    seen = []
    for _ in range(10):
        version, token, page = flow_step(client)
        if version is None:
            break
        seen.append(version)
        if "data-skip" in page:
            client.post(page_url() + "sign/", {"version": version, "action": "skip"})
        else:
            sign_step(client, version, token)
    page = client.get(page_url() + "sign/").content.decode()
    assert 'data-step="done"' in page and "You skipped 1 optional agreement" in page


def test_someone_else_sees_whose_pull_request_it_is(client, github, repository, bob):
    send_webhook(client, "pull_request", pull_payload(github, 1))
    client.force_login(bob)
    page = client.get(FLOW).content.decode()
    assert 'data-step="not-author"' in page and "by @alice" in page
    assert 'name="version"' not in page


def test_a_closed_pull_request_says_so(client, github, repository, alice):
    send_webhook(client, "pull_request", pull_payload(github, 1))
    repository.pull_requests.filter(number=1).update(open=False)
    client.force_login(alice)
    assert "The pull request is closed" in client.get(FLOW).content.decode()


def test_the_choice_is_the_first_step_when_there_is_none(client, github, policy_project, alice):
    pull = open_pull(client, github)
    pull.choice = None
    pull.choice_initialized = True
    pull.save()
    policy_project.choices.update(default=False)
    client.force_login(alice)
    page = client.get(page_url() + "sign/").content.decode()
    assert 'data-step="choose"' in page
    assert f'name="next" value="{page_url()}sign/"' in page
    response = client.post(
        page_url() + "choice/", {"choice": "ai-allowed", "next": f"{page_url()}sign/"}
    )
    assert response["Location"] == f"{page_url()}sign/"
    assert 'data-step="agreement"' in client.get(page_url() + "sign/").content.decode()


def test_the_pull_request_page_leads_into_the_flow(client, github, repository, alice):
    send_webhook(client, "pull_request", pull_payload(github, 1))
    client.force_login(alice)
    page = client.get(f"/project/{REPOSITORY}/pulls/1/").content.decode()
    assert f'href="/project/{REPOSITORY}/pulls/1/sign/" data-sign-flow' in page
    assert "Read the agreement" not in page and "<article" not in page
