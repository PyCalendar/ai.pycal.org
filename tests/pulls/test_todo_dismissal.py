"""Todos list optional agreements too; those can be dismissed until they change."""

import re

import pytest

from ai_pycal.models import TodoDismissal
from tests.pulls.test_policy_choices import open_pull

pytestmark = pytest.mark.django_db


def items(page: str) -> dict[str, str]:
    """The todos: version id -> state class."""
    return {
        pk: state for state, pk in re.findall(r'<li class="state-(\w+)" data-to-sign="(\d+)"', page)
    }


def test_optional_agreements_are_todos_that_can_be_dismissed(
    client,
    github,
    policy_project,
    alice,
):
    open_pull(client, github)
    client.force_login(alice)
    page = client.get("/todos/").content.decode()
    todos = items(page)
    optional = [pk for pk, state in todos.items() if state == "optional"]
    required = [pk for pk, state in todos.items() if state == "missing"]
    assert optional and required
    assert page.count("data-dismiss") == len(optional)
    response = client.post(f"/todos/{optional[0]}/dismiss/")
    assert response.status_code == 302 and response["Location"] == "/todos/"
    assert optional[0] not in items(client.get("/todos/").content.decode())
    assert TodoDismissal.objects.filter(version_id=optional[0]).exists()


def test_required_agreements_can_not_be_dismissed(client, github, policy_project, alice):
    open_pull(client, github)
    client.force_login(alice)
    todos = items(client.get("/todos/").content.decode())
    required = next(pk for pk, state in todos.items() if state == "missing")
    client.post(f"/todos/{required}/dismiss/")
    assert required in items(client.get("/todos/").content.decode())
    assert not TodoDismissal.objects.exists()
