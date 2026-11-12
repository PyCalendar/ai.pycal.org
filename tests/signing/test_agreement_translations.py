"""Translations of agreements: <file>.<language>.md next to the file, for reading only."""

import pytest

from ai_pycal.models import AgreementTranslation, RequiredAgreement, Signature
from ai_pycal.services.repository_sync import RepositorySync
from tests.conftest import REPOSITORY, sign_agreement

pytestmark = pytest.mark.django_db
GERMAN = {"HTTP_ACCEPT_LANGUAGE": "de"}
CLA_DE = "# Mitwirkenden-Lizenzvereinbarung\n\nDiese Übersetzung dient dem Lesen.\n"


@pytest.fixture
def cla(repository, github):
    github.push(REPOSITORY, {"agreements/cla.de.md": CLA_DE})
    RepositorySync(repository).sync()
    return RequiredAgreement.objects.get(repository=repository, key="cla")


def test_the_translation_is_read_next_to_the_file(cla):
    translation = AgreementTranslation.objects.get(version=cla.version, language="de")
    assert translation.path == "agreements/cla.de.md"
    assert translation.title == "Mitwirkenden-Lizenzvereinbarung"
    assert not AgreementTranslation.objects.filter(language="es").exists()


def test_a_translation_does_not_make_a_new_version(cla, repository, github):
    version = cla.version_id
    github.push(REPOSITORY, {"agreements/cla.de.md": CLA_DE + "\nBesser übersetzt.\n"})
    RepositorySync(repository).sync()
    cla.refresh_from_db()
    assert cla.version_id == version  # signatures stay valid
    assert "Besser übersetzt" in cla.version.translations.get(language="de").text


def test_a_removed_translation_is_removed(cla, repository, github):
    github.push(REPOSITORY, {"agreements/cla.de.md": None})
    RepositorySync(repository).sync()
    assert not AgreementTranslation.objects.exists()


def test_an_unreadable_translation_does_not_stop_the_configuration(repository, github):
    github.push(REPOSITORY, {"agreements/cla.es.md": b"\xff\xfe not text"})
    RepositorySync(repository).sync()
    repository.refresh_from_db()
    assert repository.error_code == ""
    assert not AgreementTranslation.objects.exists()


def test_german_visitors_read_the_translation_and_sign_the_original(client, cla, alice):
    page = client.get(f"/agreements/{cla.version_id}/", **GERMAN).content.decode()
    assert "Diese Übersetzung dient dem Lesen." in page
    assert 'data-translation="de"' in page
    assert 'href="?original"' in page
    original = client.get(f"/agreements/{cla.version_id}/?original", **GERMAN).content.decode()
    assert "Diese Übersetzung dient dem Lesen." not in original and "data-original" in original
    client.force_login(alice)
    sign_agreement(client, cla.version_id, "alice")
    assert Signature.objects.get().version_id == cla.version_id  # the original version


def test_other_languages_read_the_original(client, cla):
    page = client.get(f"/agreements/{cla.version_id}/", HTTP_ACCEPT_LANGUAGE="es").content.decode()
    assert "Diese Übersetzung" not in page
    assert "data-translation" not in page and "data-original" not in page


def test_the_signing_flow_shows_the_translation(client, cla, repository, github, alice):
    from tests.conftest import pull_payload, send_webhook

    github.push(REPOSITORY, {"agreements/ai-policy.de.md": "# KI-Richtlinie\n\nAuf Deutsch.\n"})
    RepositorySync(repository).sync()
    send_webhook(client, "pull_request", pull_payload(github, 1))
    client.force_login(alice)
    page = client.get(f"/project/{REPOSITORY}/pulls/1/sign/", **GERMAN).content.decode()
    assert "Auf Deutsch." in page and 'data-translation="de"' in page
