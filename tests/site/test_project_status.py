"""The status of a project: up to date or the error, with how to fix it."""

import pytest

from tests.conftest import REPOSITORY

pytestmark = pytest.mark.django_db
STATUS = f"/project/{REPOSITORY}/status/"


def test_an_up_to_date_project(client, repository):
    page = client.get(STATUS).content.decode()
    assert 'data-project-state="working"' in page and "Up to date" in page
    assert "format 2.1.0" in page
    project = client.get(f"/project/{REPOSITORY}/").content.decode()
    assert f'href="{STATUS}" data-status="working"' in project


def test_an_error_leads_to_the_status_and_the_fix(client, repository):
    repository.error_code = "ConfigFileNotFound"
    repository.error_detail = ".github/agreements.yml"
    repository.save()
    projects = client.get("/projects/").content.decode()
    assert f'href="{STATUS}" data-status="error"' in projects
    page = client.get(STATUS).content.decode()
    assert 'data-project-state="error"' in page and "<code>.github/agreements.yml</code>" in page
    assert "errors.html#ai_pycal.errors.config_file.ConfigFileNotFound" in page
    assert "How to fix it" in page


def test_private_projects_have_no_public_status(client, repository):
    repository.private = True
    repository.save()
    assert client.get(STATUS).status_code == 404
