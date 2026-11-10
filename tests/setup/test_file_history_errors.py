"""Malformed file history is a documented project error, never a new version."""

import httpx
import pytest

from ai_pycal.github import client as module
from tests.conftest import REPOSITORY

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("data", [None, {}, [None], [{}], [{"sha": "not-a-commit"}], [{"sha": 12}]])
def test_invalid_file_history_is_shown(client, github, example, maintainer, monkeypatch, data):
    original = github.handle

    def malformed(request):
        if request.url.path.endswith("/commits"):
            return httpx.Response(200, json=data)
        return original(request)

    monkeypatch.setattr(module, "TRANSPORT", httpx.MockTransport(malformed))
    client.force_login(maintainer)
    response = client.post(f"/setup/1/{example.repositories[REPOSITORY].id}/add/")
    assert response.status_code == 502
    assert b'data-error="GitHubFileHistoryInvalid"' in response.content
    assert b"errors.html#ai_pycal.errors.github.GitHubFileHistoryInvalid" in response.content


def test_empty_history_means_the_agreement_file_is_missing(
    client, github, example, maintainer, monkeypatch
):
    original = github.handle

    def missing(request):
        if request.url.path.endswith("/commits"):
            return httpx.Response(200, json=[])
        return original(request)

    monkeypatch.setattr(module, "TRANSPORT", httpx.MockTransport(missing))
    client.force_login(maintainer)
    response = client.post(f"/setup/1/{example.repositories[REPOSITORY].id}/add/")
    assert response.status_code == 404
    assert b'data-error="AgreementFileNotFound"' in response.content


def test_a_successful_retry_resolves_the_file_history_problem(
    client, github, example, maintainer, monkeypatch
):
    from ai_pycal.models import ProjectProblem

    original = github.handle

    def malformed(request):
        if request.url.path.endswith("/commits"):
            return httpx.Response(200, json={})
        return original(request)

    client.force_login(maintainer)
    target = f"/setup/1/{example.repositories[REPOSITORY].id}/add/"
    monkeypatch.setattr(module, "TRANSPORT", httpx.MockTransport(malformed))
    assert client.post(target).status_code == 502
    assert ProjectProblem.objects.get(code="GitHubFileHistoryInvalid").active
    monkeypatch.setattr(module, "TRANSPORT", github.transport())
    assert client.post(target).status_code == 302
    assert not ProjectProblem.objects.get(code="GitHubFileHistoryInvalid").active
