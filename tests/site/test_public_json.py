"""Every public page has its information as JSON at <page>.json, readable by other sites."""

import pytest

from ai_pycal.public_json import CORS, JSON_PAGES
from ai_pycal.services.public_data import json_address
from tests.conftest import REPOSITORY, pull_payload, send_webhook
from tests.pulls.test_policy_choices import accept_required, open_pull
from tests.pulls.test_policy_choices import policy_project as policy_project

pytestmark = pytest.mark.django_db


@pytest.fixture
def signed(client, github, policy_project, alice):
    """A pull request of alice with the agreements she signed."""
    item = open_pull(client, github)
    client.force_login(alice)
    accept_required(client)
    client.logout()
    return item


def read(client, path: str, status: int = 200) -> dict:
    response = client.get(path)
    assert response.status_code == status, (path, response.content[:300])
    assert response["Content-Type"] == "application/json"
    for name, value in CORS.items():
        assert response[name] == value
    return response.json()


def test_the_start_page(client, signed):
    found = read(client, "/index.json")
    assert found["projects"] == 1 and found["signatures"] >= 1
    assert found["pages"]["projects"]["json"] == "/projects.json"


def test_the_projects(client, signed):
    found = read(client, "/projects.json")
    (project,) = found["projects"]
    assert project["full_name"] == REPOSITORY
    assert project["json"] == f"/project/{REPOSITORY}.json"
    assert {agreement["key"] for agreement in project["agreements"]} >= {"cla", "ai"}
    assert read(client, "/projects/PyCalendar.json")["owner"] == "PyCalendar"
    assert read(client, "/projects/nobody.json")["projects"] == []


def test_a_project(client, signed):
    found = read(client, f"/project/{REPOSITORY}.json")
    assert found["project"]["github"] == f"https://github.com/{REPOSITORY}"
    signers = {
        agreement["key"]: [s["contributor"]["login"] for s in agreement["signatures"]]
        for agreement in found["agreements"]
    }
    assert "alice" in signers["ai"]
    assert found["choices"] and found["choices"][0]["agreements"]
    (pull,) = found["pull_requests"]
    assert pull["number"] == signed.number and pull["author"]["login"] == "alice"
    assert pull["json"] == f"/project/{REPOSITORY}/pulls/{signed.number}.json"
    assert found["status"]["json"] == f"/project/{REPOSITORY}/status.json"


def test_a_pull_request(client, signed):
    found = read(client, f"/project/{REPOSITORY}/pulls/{signed.number}.json")
    assert found["pull_request"]["state"] in {"signed", "optional"}  # what is required, signed
    assert found["choice"]["key"]
    required = [agreement for agreement in found["agreements"] if agreement["required"]]
    assert required and all(agreement["signed"] for agreement in required)
    assert found["log"]["json"] == f"/logs/{REPOSITORY}/pulls/{signed.number}.json"


def test_the_status_of_a_project(client, signed):
    found = read(client, f"/project/{REPOSITORY}/status.json")
    assert found["error"] is None and found["problems"] == []
    assert found["configuration"]["version"]


def test_a_contributor(client, signed):
    found = read(client, "/contributor/alice.json")
    assert found["login"] == "alice"
    assert {s["state"] for s in found["signatures"]} == {"valid"}
    assert found["signatures"][0]["projects"][0]["full_name"] == REPOSITORY
    assert found["pull_requests"][0]["number"] == signed.number


def test_an_agreement_its_history_and_changes(client, signed, policy_project):
    version = policy_project.required_agreements.get(key="ai").version
    found = read(client, f"/agreements/{version.pk}.json")
    assert found["text"] == version.text and found["commit"] == version.commit
    assert found["required_by"][0]["project"]["full_name"] == REPOSITORY
    history = read(client, found["history"]["json"])
    assert [row["id"] for row in history["versions"]] == [version.pk]
    changes = read(client, f"/agreements/{version.pk}/changes/{version.pk}.json")
    assert changes["version"]["id"] == version.pk and changes["changes"] == []


def test_the_logs(client, github, repository):
    send_webhook(client, "pull_request", pull_payload(github, 1))
    for path in (
        "/logs/PyCalendar.json",
        f"/logs/{REPOSITORY}.json",
        f"/logs/{REPOSITORY}/pulls/1.json",
        "/logs/contributor/alice.json",
    ):
        found = read(client, path)
        assert found["page"] == 1 and found["pages"] >= 1
    pull_log = read(client, f"/logs/{REPOSITORY}/pulls/1.json")
    assert pull_log["pull_request"]["number"] == 1
    assert pull_log["triggers"][0]["actions"]


def test_the_about_and_licenses(client, db):
    assert "build" in read(client, "/about.json")
    licenses = read(client, "/licenses.json")
    assert licenses["license"] == "AGPL-3.0-or-later" and licenses["packages"]


def test_the_json_is_public_also_with_a_session(client, signed, policy_project, alice):
    policy_project.private = True
    policy_project.save()
    client.force_login(alice)  # alice may see the private project on its page
    assert client.get(f"/project/{REPOSITORY}/").status_code == 200
    found = read(client, f"/project/{REPOSITORY}.json", status=404)
    assert found["error"] == "RepositoryNotFound" and found["documentation"]
    assert read(client, "/projects.json")["projects"] == []


def test_personal_pages_have_no_json(client, alice):
    client.force_login(alice)
    for path in (
        "/todos.json",
        "/profile.json",
        "/my-agreements.json",
        "/setup.json",
        "/logs/all.json",
    ):
        assert read(client, path, status=404)["error"] == "NotFound"


def test_unknown_addresses(client, db):
    assert read(client, "/nothing.json", status=404)["error"] == "NotFound"
    assert read(client, "/project/a/b/c/d.json", status=404)["error"] == "NotFound"


def test_javascript_of_other_sites_may_read_it(client, db):
    response = client.options("/projects.json", HTTP_ORIGIN="https://example.org")
    assert response.status_code == 204
    assert response["Access-Control-Allow-Origin"] == "*"
    assert "GET" in response["Access-Control-Allow-Methods"]


def test_the_json_can_only_be_read(client, db):
    response = client.post("/projects.json")
    assert response.status_code == 405 and response.json()["error"] == "MethodNotAllowed"


def test_the_status_of_a_policy_also_allows_other_sites(client, signed):
    response = client.get(f"/project/{REPOSITORY}/contributor/alice/ai.json")
    assert response["Access-Control-Allow-Origin"] == "*"


def test_the_html_is_unchanged(client, signed):
    response = client.get(f"/project/{REPOSITORY}/")
    assert response["Content-Type"].startswith("text/html")
    assert "Access-Control-Allow-Origin" not in response


def test_every_page_with_json_exists():
    from django.urls import get_resolver

    names = {name for name in get_resolver().reverse_dict if isinstance(name, str)}
    assert names >= JSON_PAGES


@pytest.mark.parametrize(
    ("page", "json"),
    [("/", "/index.json"), ("/projects/", "/projects.json"), ("/a/b/", "/a/b.json")],
)
def test_the_address_of_the_json(page, json):
    assert json_address(page) == json
