"""Links to the documentation next to things are a question mark in a circle, in a new tab."""

import re

import pytest
from django.template import Context, Template

pytestmark = pytest.mark.django_db


def test_the_question_mark_opens_a_new_tab():
    html = Template('{% load help %}{% help_link url "Email for new permissions" %}').render(
        Context({"url": "https://docs.example/x.html"})
    )
    assert 'class="help-link"' in html
    assert 'target="_blank" rel="noopener"' in html
    assert 'aria-label="Help: Email for new permissions (opens in a new tab)"' in html
    assert '<span aria-hidden="true">?</span>' in html


def test_the_email_for_new_permissions_is_explained(client, repository, maintainer, github):
    client.force_login(maintainer)
    page = client.get("/setup/").content.decode()
    label = page.split("Email of the installation</label>")[1].split("</a>")[0]
    assert "tutorial/admin.html#permission-email" in label
    assert 'class="help-link"' in label


def test_errors_of_projects_link_their_description_as_help(client, repository):
    repository.error_code = "ConfigFileNotFound"
    repository.save()
    page = client.get(f"/project/{repository.full_name}/").content.decode()
    assert re.search(r'class="help-link" href="[^"]+ConfigFileNotFound"', page)
    assert "How to resolve" not in page


def test_the_section_of_the_documentation_exists():
    from pathlib import Path

    docs = Path(__file__).parents[2] / "docs" / "tutorial" / "admin.rst"
    assert ".. _permission-email:" in docs.read_text()
