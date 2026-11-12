"""Administrators update a project from its page; labels are settings behind a gear."""

import pytest

from ai_pycal.models import RequiredAgreement
from tests.conftest import REPOSITORY

pytestmark = pytest.mark.django_db
URL = f"/project/{REPOSITORY}/"


def test_labels_are_behind_the_gear(client, repository):
    page = client.get(URL).content.decode()
    cla = page.split('data-policy="cla"')[1].split("</section>")[0]
    settings = cla.split("data-settings")[1].split("</details>")[0]
    assert "<code>cla-signed</code>" in settings
    assert "<code>cla-missing</code>" in settings
    outside = cla.replace(settings, "")
    assert "cla-signed" not in outside and "PR labels" not in page


def test_administrators_see_the_update_button(client, repository, maintainer):
    assert "data-update" not in client.get(URL).content.decode()
    client.force_login(maintainer)
    assert "data-update" not in client.get(URL).content.decode()
    repository.installation.admins.add(maintainer)
    page = client.get(URL).content.decode()
    assert page.index("<h2>Pull requests</h2>") < page.index("data-update")


def test_update_reads_the_configuration_again(client, github, repository, maintainer):
    repository.installation.admins.add(maintainer)
    client.force_login(maintainer)
    github.push(REPOSITORY, {"agreements/cla.md": "# CLA\n\nChanged."})
    old = RequiredAgreement.objects.get(repository=repository, key="cla").version_id
    response = client.post(f"/project/{REPOSITORY}/update/")
    assert response.status_code == 302 and response["Location"] == URL
    assert RequiredAgreement.objects.get(repository=repository, key="cla").version_id != old
    assert "The configuration was read again" in client.get(URL).content.decode()


def test_an_error_of_the_configuration_is_a_message(client, github, repository, maintainer):
    repository.installation.admins.add(maintainer)
    client.force_login(maintainer)
    github.push(REPOSITORY, {".github/agreements.yml": "version: 9.0.0\nagreements: {}\n"})
    client.post(f"/project/{REPOSITORY}/update/")
    page = client.get(URL).content.decode()
    assert "message-error" in page


def test_others_may_not_update(client, repository, alice):
    client.force_login(alice)
    assert client.post(f"/project/{REPOSITORY}/update/").status_code == 403
    assert client.get(f"/project/{REPOSITORY}/update/").status_code == 405
