"""The agreements of a project have badges, and those that need attention are listed on top."""

import pytest

from ai_pycal.models import RequiredAgreement
from ai_pycal.services.repository_sync import RepositorySync
from tests.conftest import REPOSITORY, sign_agreement

pytestmark = pytest.mark.django_db
URL = f"/project/{REPOSITORY}/"


def card(page: str, key: str) -> str:
    return page.split(f'data-policy="{key}"')[1].split("</h3>")[0]


@pytest.fixture
def agreements(repository):
    ai = RequiredAgreement.objects.get(repository=repository, key="ai-policy")
    ai.mandatory = False
    ai.save()
    return ai, RequiredAgreement.objects.get(repository=repository, key="cla")


def test_visitors_see_mandatory_and_optional(client, agreements):
    page = client.get(URL).content.decode()
    assert 'data-kind="optional"' in card(page, "ai-policy")
    assert 'data-kind="mandatory"' in card(page, "cla")
    assert "data-state" not in page
    assert "data-attention" not in page


def test_unsigned_mandatory_needs_attention(client, agreements, alice):
    client.force_login(alice)
    page = client.get(URL).content.decode()
    assert 'data-state="unsigned"' in card(page, "cla")
    assert 'data-state="unsigned"' in card(page, "ai-policy")
    attention = page.split("data-attention")[1].split("</section>")[0]
    assert "Contributor License Agreement" in attention  # mandatory
    assert "AI Policy" not in attention  # optional and unsigned: no attention


def test_signed_agreements_need_no_attention(client, agreements, alice):
    ai, cla = agreements
    client.force_login(alice)
    sign_agreement(client, cla.version_id, "alice")
    page = client.get(URL).content.decode()
    assert 'data-state="signed"' in card(page, "cla")
    assert "data-attention" not in page


@pytest.mark.parametrize("key", ["cla", "ai-policy"])
def test_outdated_signatures_need_attention(client, github, repository, agreements, alice, key):
    client.force_login(alice)
    old = RequiredAgreement.objects.get(repository=repository, key=key)
    sign_agreement(client, old.version_id, "alice")
    path = "agreements/cla.md" if key == "cla" else "agreements/ai-policy.md"
    github.push(REPOSITORY, {path: "# Changed\n\nA new version."})
    RepositorySync(repository).sync()
    page = client.get(URL).content.decode()
    assert 'data-state="outdated"' in card(page, key)
    attention = page.split("data-attention")[1].split("</section>")[0]
    assert "It changed since you signed it." in attention
