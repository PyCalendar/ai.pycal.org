"""The title of an agreement is shown once: the same first heading of its text is left out."""

import pytest

from ai_pycal.models import RequiredAgreement
from ai_pycal.services.repository_sync import RepositorySync
from tests.conftest import REPOSITORY, pull_payload, send_webhook

pytestmark = pytest.mark.django_db
CLA = "Contributor License Agreement (example)"


def article(page: str) -> str:
    return page.split('class="card agreement" id="agreement">')[1].split("</article>")[0]


def cla_page(client, repository) -> tuple[RequiredAgreement, str]:
    cla = RequiredAgreement.objects.get(repository=repository, key="cla")
    return cla, client.get(f"/agreements/{cla.version_id}/").content.decode()


def test_the_page_of_an_agreement_shows_its_title_once(client, repository):
    cla, page = cla_page(client, repository)
    assert cla.version.text.startswith(f"# {CLA}")
    assert f'<h1 class="crumbs-current"><a href="/agreements/{cla.version_id}/">{CLA}</a>' in page
    assert CLA not in article(page) and "<h1>" not in article(page)
    assert page.count(f">{CLA}</a></h1>") == 1


def test_the_signing_flow_shows_the_title_once(client, repository, github, alice):
    send_webhook(client, "pull_request", pull_payload(github, 1))
    client.force_login(alice)
    page = client.get(f"/project/{REPOSITORY}/pulls/1/sign/").content.decode()
    step = page.split('data-step="agreement"')[1].split("</section>")[0]
    heading, text = step.split('<article class="agreement">')
    assert "<h1>" in heading
    assert "<h1>" not in text.split("</article>")[0]


def test_front_matter_is_not_shown_and_does_not_make_the_title(client, repository, github):
    github.push(
        REPOSITORY,
        {
            "agreements/cla.md": (
                f"---\nlayout: agreement\n# a comment of YAML\n---\n# {CLA}\n\nI agree.\n"
            )
        },
    )
    RepositorySync(repository).sync()
    cla, page = cla_page(client, repository)
    assert cla.version.title == CLA
    shown = article(page)
    assert "layout" not in shown and "comment" not in shown and "<hr" not in shown
    assert "<h1>" not in shown and "I agree." in shown


def test_another_first_heading_stays(client, repository, github):
    github.push(REPOSITORY, {"agreements/cla.md": "Intro.\n\n# Part one\n\nI agree.\n"})
    RepositorySync(repository).sync()
    cla, page = cla_page(client, repository)
    assert "<h1>Part one</h1>" in article(page)
