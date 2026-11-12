"""Public policy records, agreement histories, badges and private project visibility."""

import pytest
from django.utils import timezone

from ai_pycal.models import AgreementVersion
from ai_pycal.services.repository_sync import RepositorySync
from tests.conftest import REPOSITORY, sign_agreement
from tests.pulls.test_policy_choices import CONFIG, accept_required, open_pull
from tests.pulls.test_policy_choices import policy_project as policy_project

pytestmark = pytest.mark.django_db


def test_public_records_status_and_badge(client, github, policy_project, alice):
    open_pull(client, github)
    endpoint = f"/project/{REPOSITORY}/contributor/alice/ai"
    unsigned = client.get(endpoint + ".json")
    assert unsigned.status_code == 200
    assert unsigned.json()["signed"] is False
    client.force_login(alice)
    accept_required(client)
    client.logout()
    result = client.get(endpoint + ".json").json()
    assert result["signed"] is True
    assert result["signed_at"]
    assert result["agreement"]["path"] == "agreements/ai-policy.md"
    assert result["mandatory"] is False
    badge = client.get(endpoint + ".svg")
    assert badge["Content-Type"] == "image/svg+xml"
    assert b"ai: signed" in badge.content
    assert badge["Cache-Control"] == "no-store"
    page = client.get(f"/project/{REPOSITORY}/").content.decode()
    assert "@alice" in page and timezone.now().strftime("%Y-%m-%d") in page
    contributor = client.get("/contributor/alice/").content.decode()
    assert REPOSITORY in contributor and "Valid for" in contributor
    assert "<details><summary>Other projects" in contributor
    missing = client.get(f"/project/{REPOSITORY}/contributor/alice/missing.json")
    assert missing.status_code == 404
    assert missing.json()["error"] == "AgreementNotFound"
    assert missing.json()["documentation"].endswith("AgreementNotFound")


def test_new_version_invalidates_public_status_without_erasing_history(
    client, github, policy_project, alice
):
    client.force_login(alice)
    agreement = policy_project.required_agreements.get(key="ai")
    old = agreement.version
    assert sign_agreement(client, old.pk, "alice").status_code == 302
    github.push(REPOSITORY, {"agreements/ai-policy.md": "# Updated AI policy"})
    RepositorySync(policy_project).sync()
    result = client.get(f"/project/{REPOSITORY}/contributor/alice/ai.json").json()
    assert not result["signed"]
    assert result["agreement"]["commit"] != old.commit
    histories = client.get("/agreements/").content.decode()
    assert f"/agreements/history/{REPOSITORY}/agreements/ai-policy.md/" in histories
    history = client.get(
        f"/agreements/history/{REPOSITORY}/agreements/ai-policy.md/"
    ).content.decode()
    assert old.short_commit in history and result["agreement"]["commit"][:7] in history
    assert client.get(f"/agreements/{old.pk}/").status_code == 200
    assert "agreements/ai-policy.md" in client.get("/contributor/alice/").content.decode()


def test_same_commit_and_path_from_different_sources_are_separate_histories(db):
    one = AgreementVersion.objects.create(
        source="one/repo", commit="a" * 40, path="policy.md", text="one"
    )
    two = AgreementVersion.objects.create(
        source="two/repo", commit="a" * 40, path="policy.md", text="two"
    )
    assert one.pk != two.pk


def test_private_project_records_never_appear_to_anonymous_visitors(
    client, github, policy_project, alice
):
    item = open_pull(client, github)
    client.force_login(alice)
    accept_required(client)
    client.logout()
    policy_project.private = True
    policy_project.save()
    version = policy_project.required_agreements.get(key="ai").version
    for url in [
        f"/repository/{REPOSITORY}/",
        f"/repository/{REPOSITORY}/pull/{item.number}/",
        f"/project/{REPOSITORY}/",
        f"/project/{REPOSITORY}/pulls/{item.number}/",
        f"/project/{REPOSITORY}/contributor/alice/ai.json",
        f"/project/{REPOSITORY}/contributor/alice/ai.svg",
        f"/agreements/{version.pk}/",
        f"/agreements/history/{REPOSITORY}/agreements/ai-policy.md/",
    ]:
        assert client.get(url).status_code == 404, url
    for url in ["/projects/", "/agreements/", "/contributor/alice/"]:
        assert REPOSITORY not in client.get(url).content.decode()


def test_unknown_contributor_and_history_are_well_defined(client, policy_project):
    assert client.get("/contributor/unknown/").status_code == 200
    assert (
        client.get(f"/project/{REPOSITORY}/contributor/unknown/ai.json").json()["signed"] is False
    )
    assert client.get(f"/agreements/history/{REPOSITORY}/missing.md/").status_code == 404


def test_home_links_to_public_directories(client):
    page = client.get("/").content.decode()
    assert 'href="/projects/"' in page and 'href="/agreements/"' in page
    assert ">Browse agreements</a>" in page


def test_public_pages_call_them_agreements(client, policy_project, alice):
    client.force_login(alice)
    for url, expected in [
        ("/", ">Browse agreements</a>"),
        ("/agreements/", "<h1>Agreements</h1>"),
        (f"/project/{REPOSITORY}/", ">Agreement</a>"),
        (f"/agreements/history/{REPOSITORY}/agreements/ai-policy.md/", "<p>Agreement</p>"),
    ]:
        response = client.get(url)
        assert response.status_code == 200
        page = response.content.decode()
        assert expected in page
        assert ">Agreements</a>" in page
        assert "Agreement history" not in page
        assert "Agreement histories" not in page


def test_policy_descriptions_are_safe_markdown(client, github, policy_project):
    github.push(
        REPOSITORY,
        {
            ".github/agreements.yml": CONFIG.replace(
                "**Responsible AI use**", "<script>alert(1)</script> **Responsible AI use**"
            )
        },
    )
    RepositorySync(policy_project).sync()
    page = client.get(f"/project/{REPOSITORY}/").content.decode()
    assert "<strong>Responsible AI use</strong>" in page
    assert "<script>" not in page


def test_mandatory_agreements_come_first(client, repository):
    first, second = repository.required_agreements.order_by("position")
    first.mandatory = False
    first.save()
    assert list(repository.required_agreements.all()) == [second, first]
    page = client.get(f"/project/{repository.full_name}/").content.decode()
    assert page.index(second.name) < page.index(first.name)
