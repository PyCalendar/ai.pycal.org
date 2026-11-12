"""The page of an agreement is simple: its path in the site, the text and the form to sign."""

import re
from html import unescape

import pytest

from ai_pycal.models import RequiredAgreement, Signature
from ai_pycal.views.agreements import handle_pattern
from tests.conftest import sign_agreement

pytestmark = pytest.mark.django_db


@pytest.fixture
def cla(repository):
    return RequiredAgreement.objects.get(repository=repository, key="cla")


def test_the_path_of_the_agreement_is_the_title(client, cla):
    page = client.get(f"/agreements/{cla.version_id}/").content.decode()
    title = page.split('<h1 class="crumbs-path">')[1].split("</h1>")[0]
    assert title == (
        '<a href="/projects/PyCalendar/">PyCalendar</a><span class="crumbs-sep">/</span>'
        '<a href="/project/PyCalendar/ai.pycal.org-example/">ai.pycal.org-example</a>'
        '<span class="crumbs-sep">/</span>'
        f'<a href="/agreements/{cla.version_id}/">Contributor License Agreement (example)</a>'
    )


def test_the_other_agreements_of_the_project_are_in_a_menu(client, cla, repository):
    ai = repository.required_agreements.get(key="ai-policy")
    page = client.get(f"/agreements/{cla.version_id}/").content.decode()
    menu = page.split('<details class="crumb-menu">')[1].split("</details>")[0]
    assert f'<a href="/agreements/{ai.version_id}/">{ai.name}</a>' in menu
    assert cla.name not in menu


def test_one_agreement_has_no_menu(client, cla, repository):
    repository.required_agreements.exclude(pk=cla.pk).delete()
    assert 'class="crumb-menu"' not in client.get(f"/agreements/{cla.version_id}/").content.decode()


def test_the_details_are_at_the_bottom(client, cla):
    page = client.get(f"/agreements/{cla.version_id}/").content.decode()
    assert page.index('id="agreement"') < page.index("data-details")
    details = page.split("data-details")[1]
    assert "agreements/cla.md of PyCalendar/ai.pycal.org-example" in details
    assert "asked for by" in details


def test_the_owner_page_lists_the_projects_of_the_owner(client, repository):
    assert repository.full_name in client.get("/projects/PyCalendar/").content.decode()
    assert repository.full_name not in client.get("/projects/someone-else/").content.decode()


@pytest.mark.parametrize("typed", ["alice", "ALICE", "@Alice", " alice "])
def test_the_browser_checks_the_handle(client, cla, alice, typed):
    client.force_login(alice)
    page = client.get(f"/agreements/{cla.version_id}/").content.decode()
    pattern = unescape(re.search(r'pattern="([^"]+)"', page).group(1))
    assert pattern == handle_pattern("alice")
    assert re.fullmatch(pattern, typed)  # as the browser: the whole value
    assert not re.fullmatch(pattern, "bob")
    assert not re.fullmatch(pattern, "alicex")


def test_a_wrong_handle_shows_the_page_again_with_the_reason(client, cla, alice):
    client.force_login(alice)
    response = sign_agreement(client, cla.version_id, "bob", next="/project/x/y/pulls/1/")
    assert response.status_code == 400
    page = response.content.decode()
    assert 'data-error="HandleMismatch"' in page
    assert 'id="agreement"' in page  # the agreement, not an error page
    assert 'name="handle" value="bob"' in page
    assert 'name="next" value="/project/x/y/pulls/1/"' in page
    assert not Signature.objects.exists()


def test_a_handle_with_regex_characters_is_escaped():
    assert handle_pattern("a-1") == r"\s*@?[aA]-1\s*"
