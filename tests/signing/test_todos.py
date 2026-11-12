"""The menu of the account, the page Todos, and agreements to sign again after a change."""

import pytest

from ai_pycal.models import RequiredAgreement
from ai_pycal.services.repository_sync import RepositorySync
from tests.conftest import REPOSITORY, pull_payload, send_webhook, sign_agreement

pytestmark = pytest.mark.django_db


@pytest.fixture
def cla(repository):
    return RequiredAgreement.objects.get(repository=repository, key="cla")


def test_the_menu_of_the_account(client, alice):
    client.force_login(alice)
    page = client.get("/").content.decode()
    menu = page.split('<details class="account-menu">')[1].split("</details>")[0]
    order = [
        "Todos",
        "My agreements",
        "Set up a repository",
        "Dashboard",
        "Preferences",
        "Sign out",
    ]
    positions = [menu.index(label) for label in order]
    assert positions == sorted(positions)
    assert menu.count('role="separator"') == 2
    assert "@alice" in menu.split("</summary>")[0]
    assert 'href="/contributor/alice/">Dashboard' in menu
    assert 'href="/profile/">Preferences' in menu
    assert "Admin" not in menu


def test_visitors_have_no_menu(client):
    page = client.get("/").content.decode()
    assert "account-menu" not in page
    assert "Sign in with GitHub" in page


def test_todos_list_the_agreements_of_open_pull_requests(client, github, cla, alice):
    send_webhook(client, "pull_request", pull_payload(github, 1))
    client.force_login(alice)
    page = client.get("/todos/").content.decode()
    assert page.count("data-to-sign=") == 2
    assert '<span class="count"' in page  # the number in the menu
    sign_agreement(client, cla.version_id, "alice")
    assert client.get("/todos/").content.decode().count("data-to-sign=") == 1


def test_a_changed_agreement_is_to_sign_again(client, github, repository, cla, alice):
    client.force_login(alice)
    sign_agreement(client, cla.version_id, "alice")
    assert f'data-to-sign="{cla.version_id}"' not in client.get("/todos/").content.decode()
    github.push(REPOSITORY, {"agreements/cla.md": "# Contributor License Agreement\n\nChanged."})
    RepositorySync(repository).sync()
    new = RequiredAgreement.objects.get(repository=repository, key="cla")
    assert new.version_id != cla.version_id
    for url in ("/todos/", "/my-agreements/"):
        page = client.get(url).content.decode()
        item = page.split(f'data-to-sign="{new.version_id}"')[1].split("</li>")[0]
        assert "data-signed-before" in item and "You signed an earlier version" in item
        assert f'href="/agreements/{new.version_id}/">{new.title}</a>' in item
        assert 'href="/projects/PyCalendar/">PyCalendar</a>' in item


def test_signed_agreements_are_named_not_pathed(client, cla, alice):
    client.force_login(alice)
    sign_agreement(client, cla.version_id, "alice")
    signed = client.get("/my-agreements/").content.decode().split("<tbody>")[1]
    assert f">{cla.name}</a>" in signed
    assert f'href="/project/{REPOSITORY}/">' in signed
    assert ">agreements/cla.md<" not in signed  # the path only in the address on GitHub


def test_nothing_to_do_is_said_once(client, alice):
    client.force_login(alice)
    page = client.get("/todos/").content.decode()
    main = page.split("<main")[1].split("</main>")[0]
    assert "data-nothing" in main and "Nothing to do." in main
    assert "Agreements to sign" not in main and "Nothing to sign" not in main
    assert "message-success" not in main
