"""An optional agreement that no choice lists labels the pull request when it is signed.

This is the example repository: the AI policy is optional and the CLA is mandatory. A pull
request first checked before the project offered choices gets the default choice later.
"""

import pytest

from ai_pycal.models import PullRequest
from ai_pycal.services.pull_request_check import PullRequestCheck
from ai_pycal.services.repository_sync import RepositorySync
from tests.conftest import REPOSITORY, pull_payload, send_webhook, sign_agreement
from tests.pulls.test_labels import versions

pytestmark = pytest.mark.django_db

AGREEMENTS = """
agreements:
  cla:
    name: CLA
    path: agreements/cla.md
    pr: {labels: cla-signed, unsigned-labels: cla-missing}
  ai-policy:
    name: AI Policy
    path: agreements/ai-policy.md
    mandatory: false
    pr: {labels: ai-policy-accepted}
"""
CHOICES = """
choices:
  - name: Disclosed AI use
    description: Accept the AI policy.
    agreements: [ai-policy]
    default: true
    pr: {labels: ai-disclosed}
"""


def configure(github, repository, text: str) -> None:
    github.push(REPOSITORY, {".github/agreements.yml": "version: 2.2.0\n" + text})
    RepositorySync(repository).sync()


def labels(github, number: int = 1) -> set[str]:
    return set(github.labels.get((REPOSITORY, number), []))


def test_a_signed_optional_agreement_without_choices_adds_its_label(
    client, github, repository, alice
):
    configure(github, repository, AGREEMENTS)
    send_webhook(client, "pull_request", pull_payload(github, 1))
    assert labels(github) == {"cla-missing"}  # optional: no label while it is not signed
    client.force_login(alice)
    sign_agreement(client, versions(repository)["cla"], "alice")
    assert labels(github) == {"cla-signed"}
    sign_agreement(client, versions(repository)["ai-policy"], "alice")
    assert labels(github) == {"cla-signed", "ai-policy-accepted"}
    pull = PullRequest.objects.get(number=1)
    assert pull.all_signed  # the optional agreement never blocks


def test_an_update_adds_the_label_of_an_agreement_signed_before(client, github, repository, alice):
    configure(github, repository, AGREEMENTS)
    client.force_login(alice)
    sign_agreement(client, versions(repository)["ai-policy"], "alice")
    send_webhook(client, "pull_request", pull_payload(github, 1))
    assert "ai-policy-accepted" in labels(github)
    github.labels[(REPOSITORY, 1)].remove("ai-policy-accepted")  # removed on GitHub
    PullRequestCheck(PullRequest.objects.get(number=1)).run()  # the regular update
    assert "ai-policy-accepted" in labels(github)


def test_an_optional_agreement_of_another_choice_adds_no_label(client, github, repository, alice):
    github.push(REPOSITORY, {"agreements/human.md": "# Human authorship\n\nNo AI."})
    configure(
        github,
        repository,
        AGREEMENTS
        + """
  human:
    name: Human authorship
    path: agreements/human.md
    mandatory: false
    pr: {labels: human-authored}
"""
        + CHOICES
        + """
  - name: Human
    description: No AI.
    agreements: [human]
""",
    )
    send_webhook(client, "pull_request", pull_payload(github, 1))
    client.force_login(alice)
    for pk in versions(repository).values():
        sign_agreement(client, pk, "alice")
    # human is signed, but the choice of the pull request is the disclosed AI use
    assert "human-authored" not in labels(github)
    assert {"ai-policy-accepted", "ai-disclosed", "cla-signed"} <= labels(github)


def test_choices_added_later_give_their_default_to_older_pull_requests(
    client, github, repository, alice
):
    configure(github, repository, AGREEMENTS)
    send_webhook(client, "pull_request", pull_payload(github, 1))
    pull = PullRequest.objects.get(number=1)
    assert pull.choice is None and not pull.choice_initialized  # nothing to freeze yet
    configure(github, repository, AGREEMENTS + CHOICES)
    PullRequestCheck(pull).run()
    pull.refresh_from_db()
    assert pull.choice.key == "disclosed-ai-use" and pull.choice_initialized
    client.force_login(alice)
    for pk in versions(repository).values():
        sign_agreement(client, pk, "alice")
    assert {"cla-signed", "ai-policy-accepted", "ai-disclosed"} <= labels(github)
