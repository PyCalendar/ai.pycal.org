"""The site in German and Spanish: the browser chooses first, the menu changes it."""

import re
from pathlib import Path

import pytest
from babel.messages.mofile import read_mo
from babel.messages.pofile import read_po

from tests.conftest import REPOSITORY

pytestmark = pytest.mark.django_db
LOCALE = Path(__file__).parents[2] / "ai_pycal" / "locale"
GERMAN = {"HTTP_ACCEPT_LANGUAGE": "de-DE,de;q=0.9,en;q=0.5"}


def text(page: str) -> str:
    main = page.split("<main")[1].split("</main>")[0]
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", main))


def test_the_browser_chooses_the_first_language(client, repository):
    page = client.get("/projects/", **GERMAN).content.decode()
    assert '<html lang="de"' in page
    assert "Projekte" in page and "Öffne ein Projekt" in page
    spanish = client.get("/projects/", HTTP_ACCEPT_LANGUAGE="es").content.decode()
    assert '<html lang="es"' in spanish and "Proyectos" in spanish
    assert '<html lang="en"' in client.get("/projects/", HTTP_ACCEPT_LANGUAGE="fr").content.decode()


def test_the_menu_names_each_language_in_itself(client):
    page = client.get("/", **GERMAN).content.decode()
    menu = page.split('<details class="theme-menu language-menu">')[1].split("</details>")[0]
    for code, name in (("en", "English"), ("de", "Deutsch"), ("es", "Español")):
        assert f'value="{code}" lang="{code}"' in menu and f">{name}</button>" in menu
    assert 'value="de" lang="de" aria-pressed="true"' in menu
    assert 'aria-label="Sprache"' in menu
    # next to the colors
    assert page.index("language-menu") < page.index('<details class="theme-menu">')


def test_the_menu_changes_the_language_without_javascript(client):
    response = client.post("/language/", {"language": "es", "next": "/about/"}, **GERMAN)
    assert response.status_code == 302 and response["Location"] == "/about/"
    page = client.get("/about/", **GERMAN).content.decode()  # the choice beats the browser
    assert '<html lang="es"' in page and "Acerca de" in page


def test_the_menu_does_not_leave_the_site(client):
    response = client.post("/language/", {"language": "de", "next": "https://evil.example/"})
    assert response["Location"] == "/"


def test_error_pages_are_translated(client):
    page = client.get("/no-such-page/", **GERMAN).content.decode()
    assert "Seite nicht gefunden" in page


def test_pages_in_german(client, github, repository, alice):
    from tests.conftest import pull_payload, send_webhook

    send_webhook(client, "pull_request", pull_payload(github, 1))
    for path in ("/", f"/project/{REPOSITORY}/", f"/project/{REPOSITORY}/pulls/1/"):
        assert client.get(path, **GERMAN).status_code == 200, path
    project = text(client.get(f"/project/{REPOSITORY}/", **GERMAN).content.decode())
    assert "Vereinbarungen" in project and "Pull Requests" in project


@pytest.mark.parametrize("language", ["de", "es"])
def test_every_text_is_translated_and_compiled(language):
    folder = LOCALE / language / "LC_MESSAGES"
    with open(folder / "django.po", "rb") as po:
        catalog = read_po(po, locale=language)
    with open(folder / "django.mo", "rb") as mo:
        compiled = read_mo(mo)

    def strings(message):
        return message.string if isinstance(message.string, list | tuple) else (message.string,)

    assert catalog.locale is not None and catalog.plural_forms.startswith("nplurals=2")
    missing = [m.id for m in catalog if m.id and not all(strings(m))]
    assert missing == [], f"untranslated in {language}: {missing[:5]} (make messages)"
    fuzzy = [m.id for m in catalog if m.id and m.fuzzy]
    assert fuzzy == [], f"fuzzy in {language}: {fuzzy[:5]}"
    for message in catalog:
        if message.id:

            def same(value):
                return tuple(value) if isinstance(value, list | tuple) else value

            assert same(compiled[message.id].string) == same(message.string), (
                f"{language}: django.mo is older than django.po; run make messages"
            )
