"""Contributor defaults freeze on creation and only authors can change PR choices."""

import re

import pytest
from django.test import Client

from ai_pycal.models import ContributorPreference, PullRequest, Signature
from ai_pycal.services.repository_sync import RepositorySync
from tests.conftest import ALICE, REPOSITORY, pull_payload, send_webhook

pytestmark = pytest.mark.django_db

CONFIG = """version: 2.0.0
agreements:
  cla:
    name: CLA
    path: agreements/cla.md
    mandatory: true
    pr: {labels: cla-signed}
  ai:
    name: AI policy
    description: '**Responsible AI use**'
    path: agreements/ai-policy.md
    mandatory: false
    pr: {labels: ai-signed}
  human:
    name: Human policy
    path: agreements/human.md
    mandatory: false
    pr: {labels: human-signed}
choices:
  - name: AI allowed
    description: AI contributions with disclosure.
    agreements: [ai]
    default: true
    pr: {labels: ai-choice}
  - name: Human only
    description: No AI in this contribution.
    agreements: [human]
    default: false
    pr: {labels: human-choice}
"""


@pytest.fixture
def policy_project(repository, github):
    github.push(
        REPOSITORY,
        {
            ".github/agreements.yml": CONFIG,
            "agreements/human.md": "# Human policy\nI wrote this contribution myself.",
        },
    )
    RepositorySync(repository).sync()
    repository.refresh_from_db()
    return repository


def open_pull(client, github, number=1):
    result = send_webhook(client, "pull_request", pull_payload(github, number))
    assert result.status_code == 200, result.content
    return PullRequest.objects.get(number=number)


def page_url(number=1):
    return f"/project/{REPOSITORY}/pulls/{number}/"


def flow_step(client, number=1):
    """The current step of the signing flow: its version and token, or None at the end."""
    page = client.get(page_url(number) + "sign/").content.decode()
    found = re.search(r'name="version" value="(\d+)"', page)
    if not found:
        return None, None, page
    token = re.search(r'name="shown" value="([^"]+)"', page).group(1)
    return found.group(1), token, page


def accept_required(client, number=1, optional=False):
    """Sign through the flow as a person: the required agreements, optional ones skipped."""
    response = None
    for _ in range(20):
        version, token, page = flow_step(client, number)
        if version is None:  # the end of the flow: the last signature, or nothing to sign
            return response or client.get(page_url(number) + "sign/", follow=False)
        if "data-skip" in page and not optional:
            client.post(page_url(number) + "sign/", {"version": version, "action": "skip"})
            continue
        response = client.post(
            page_url(number) + "sign/",
            {
                "version": version,
                "shown": token,
                "accept": "yes",
                "handle": "alice",
                "action": "sign",
            },
        )
        assert response.status_code == 302, response.content.decode()[:500]
    raise AssertionError("the flow did not end")


def test_default_changes_only_future_prs(client, github, policy_project, alice):
    one = open_pull(client, github, 1)
    two = open_pull(client, github, 2)
    assert one.choice.key == two.choice.key == "ai-allowed"
    client.force_login(alice)
    response = client.post(f"/project/{REPOSITORY}/default/", {"choice": "human-only"})
    assert response.status_code == 302
    one.refresh_from_db()
    two.refresh_from_db()
    assert one.choice.key == two.choice.key == "ai-allowed"
    three = open_pull(client, github, 3)
    assert three.choice.key == "human-only"
    assert client.post(page_url(1) + "choice/", {"choice": "human-only"}).status_code == 302
    one.refresh_from_db()
    two.refresh_from_db()
    assert one.choice.key == "human-only" and two.choice.key == "ai-allowed"
    page = client.get("/contributor/alice/").content.decode()
    assert page_url(1) in page and page_url(2) in page and "Existing PRs" in page


def test_signing_requires_mandatory_and_only_selected_bundle(client, github, policy_project, alice):
    item = open_pull(client, github)
    client.force_login(alice)
    assert accept_required(client).status_code in (200, 302)
    item.refresh_from_db()
    assert item.all_signed
    assert set(Signature.objects.values_list("version__path", flat=True)) == {
        "agreements/cla.md",
        "agreements/ai-policy.md",
    }
    assert set(github.labels[(REPOSITORY, 1)]) == {"cla-signed", "ai-signed", "ai-choice"}
    client.post(page_url() + "choice/", {"choice": "human-only", "default": "yes"})
    item.refresh_from_db()
    assert not item.all_signed
    assert set(github.labels[(REPOSITORY, 1)]) == {"cla-signed", "human-choice"}
    assert ContributorPreference.objects.get(github_id=ALICE[0]).choice.key == "human-only"
    assert accept_required(client).status_code in (200, 302)
    item.refresh_from_db()
    assert item.all_signed
    assert set(github.labels[(REPOSITORY, 1)]) == {"cla-signed", "human-signed", "human-choice"}
    assert Signature.objects.count() == 3  # Changing a choice preserves old signatures.


def test_only_the_author_can_choose_or_sign(client, github, policy_project, bob):
    open_pull(client, github)
    assert client.post(page_url() + "choice/", {"choice": "human-only"}).status_code == 302
    client.force_login(bob)
    for action in ("choice/", "sign/"):
        response = client.post(page_url() + action, {"choice": "human-only"})
        assert response.status_code == 403
        assert b'data-error="NotPullRequestAuthor"' in response.content
    assert Signature.objects.count() == 0


def test_public_pr_is_focused_and_never_offers_signing_for_someone_else(
    client, github, policy_project, bob
):
    open_pull(client, github)
    page = client.get(page_url()).content.decode()
    assert "Sign in to sign agreements" in page
    assert "AI allowed" in page and "Mandatory" in page
    assert "<footer" not in page and ">Setup<" not in page
    client.force_login(bob)
    page = client.get(page_url()).content.decode()
    assert 'name="accept_' not in page and 'name="choice"' not in page
    assert "public agreement record" in page


def test_forged_display_tokens_cannot_sign_anything(client, github, policy_project, alice):
    open_pull(client, github)
    client.force_login(alice)
    response = client.post(page_url() + "sign/", {"handle": "alice"})
    assert response.status_code == 400
    assert Signature.objects.count() == 0


def test_choice_changes_require_post_csrf_and_a_current_project_choice(
    client, github, policy_project, alice
):
    open_pull(client, github)
    client.force_login(alice)
    assert client.get(page_url() + "choice/").status_code == 405
    response = client.post(page_url() + "choice/", {"choice": "missing"})
    assert response.status_code == 404
    assert b'data-error="ChoiceNotFound"' in response.content
    strict = Client(enforce_csrf_checks=True)
    strict.force_login(alice)
    assert strict.post(page_url() + "choice/", {"choice": "human-only"}).status_code == 403


def test_no_default_leaves_choice_pending(client, github, policy_project):
    github.push(
        REPOSITORY, {".github/agreements.yml": CONFIG.replace("default: true", "default: false")}
    )
    item = open_pull(client, github)
    assert item.choice_id is None
    assert not item.all_signed
    status = github.status(REPOSITORY, item.head_sha, "ai.example.org/choices/selection")
    assert status["state"] == "pending"


def test_configuration_default_changes_do_not_change_existing_prs(client, github, policy_project):
    item = open_pull(client, github)
    changed = CONFIG.replace("default: true", "default: false", 1)
    changed = changed.replace(
        "name: Human only\n    description:", "name: Human only\n    description:"
    )
    github.push(REPOSITORY, {".github/agreements.yml": changed})
    RepositorySync(policy_project).sync()
    item.refresh_from_db()
    assert item.choice.key == "ai-allowed"


def test_removed_choice_requires_new_explicit_choice(client, github, policy_project):
    item = open_pull(client, github)
    github.push(
        REPOSITORY,
        {
            ".github/agreements.yml": CONFIG.split("  - name: Human only")[0].replace(
                "name: AI allowed", "name: Another choice"
            )
        },
    )
    RepositorySync(policy_project).sync()
    item.refresh_from_db()
    assert item.choice_id is None
    from ai_pycal.services.pull_request_check import PullRequestCheck

    PullRequestCheck(item).run()
    assert not item.all_signed  # The new project default must not silently replace it.


def test_removed_labels_and_checks_are_reconciled_without_touching_other_labels(
    client, github, policy_project, alice
):
    item = open_pull(client, github)
    client.force_login(alice)
    accept_required(client)
    github.labels[(REPOSITORY, 1)].append("unrelated")
    changed = CONFIG.replace("ai-choice", "new-ai-choice").replace("ai-signed", "new-ai-signed")
    github.push(REPOSITORY, {".github/agreements.yml": changed})
    assert send_webhook(client, "pull_request", pull_payload(github, 1)).status_code == 200
    # Changing configuration leaves agreement signatures valid. Old labels
    # must be replaced by the newly configured labels immediately.
    labels = set(github.labels[(REPOSITORY, 1)])
    assert "ai-choice" not in labels and "ai-signed" not in labels
    assert "new-ai-choice" in labels and "new-ai-signed" in labels
    assert "unrelated" in labels
    # Removing an agreement must neutralize its previous check, rather than
    # leave a stale pending result on the current head SHA.
    import yaml

    data = yaml.safe_load(changed)
    data["agreements"].pop("human")
    data["choices"] = data["choices"][:1]
    github.push(REPOSITORY, {".github/agreements.yml": yaml.safe_dump(data)})
    assert send_webhook(client, "pull_request", pull_payload(github, 1)).status_code == 200
    assert github.status(REPOSITORY, item.head_sha, "ai.example.org/human")["state"] == "success"


def test_a_forged_token_signs_nothing(client, github, policy_project, alice):
    open_pull(client, github)
    client.force_login(alice)
    version, _token, _page = flow_step(client)
    response = client.post(
        page_url() + "sign/",
        {
            "version": version,
            "shown": "forged",
            "accept": "yes",
            "handle": "alice",
            "action": "sign",
        },
    )
    assert response.status_code == 400
    assert 'data-error="AgreementNotShown"' in response.content.decode()
    assert Signature.objects.count() == 0


def test_selected_choice_is_authorized_but_does_not_sign_agreements(
    client, github, policy_project, alice
):
    open_pull(client, github)
    client.force_login(alice)
    assert client.post(page_url() + "choice/", {"choice": "human-only"}).status_code == 302
    assert Signature.objects.count() == 0
    assert "human-choice" in github.labels[(REPOSITORY, 1)]
    assert 'data-step="agreement"' in client.get(page_url() + "sign/").content.decode()
    assert Signature.objects.count() == 0  # the flow shows the agreements, signs nothing


def test_every_agreement_is_listed_with_its_color(client, github, policy_project, alice):
    open_pull(client, github)
    client.force_login(alice)
    page = client.get(page_url()).content.decode()
    states = dict(re.findall(r'data-agreement="([\w-]+)" data-state="(\w+)"', page))
    assert set(states) == {a.key for a in policy_project.required_agreements.all()}
    assert "missing" in states.values() and "optional" in states.values()
    assert "Other project agreements" not in page and "Project agreements</a>" not in page
    accept_required(client)
    page = client.get(page_url()).content.decode()
    states = dict(re.findall(r'data-agreement="([\w-]+)" data-state="(\w+)"', page))
    assert "missing" not in states.values() and "signed" in states.values()


def test_optional_agreements_can_be_signed_in_the_flow(client, github, policy_project, alice):
    open_pull(client, github)
    client.force_login(alice)
    accept_required(client, optional=True)
    assert Signature.objects.count() == policy_project.required_agreements.count()


def test_the_title_has_the_path_and_a_menu_of_my_pull_requests(
    client, github, policy_project, alice
):
    open_pull(client, github, 1)
    open_pull(client, github, 2)
    client.force_login(alice)
    page = client.get(page_url(1)).content.decode()
    title = page.split("data-title>")[1].split("</h1>")[0]
    assert '<a href="/projects/PyCalendar/">PyCalendar</a>' in title and ">#1</a>" in title
    assert title.index("pull-menu") < title.index(">#1</a>")
    menu = page.split('class="crumb-menu pull-menu"')[1].split("</details>")[0]
    assert menu.index("#2</span>") < menu.index("#1</span>")  # the highest number first
    filtered = client.get(page_url(1) + "?q=%232").content.decode()
    menu = filtered.split('class="crumb-menu pull-menu"')[1].split("</details>")[0]
    assert "#2</span>" in menu and "#1</span>" not in menu
    assert 'pull-menu" open' in filtered
