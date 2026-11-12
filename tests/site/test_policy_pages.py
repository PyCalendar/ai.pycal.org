"""Public policy records, agreement histories, badges and private project visibility."""

import re

import pytest

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
    # the open pull request with its author and state, no list of signers
    assert 'href="/contributor/alice/">@alice</a>' in page and "data-pull-state=" in page
    assert "No signatures yet" not in page
    contributor = client.get("/contributor/alice/").content.decode()
    assert REPOSITORY in contributor and "valid for" in contributor
    assert "Other projects" not in contributor  # no other projects: no section
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
    assert client.get("/agreements/").status_code == 404  # the list of agreements is gone
    history = client.get(
        f"/agreements/history/{REPOSITORY}/agreements/ai-policy.md/"
    ).content.decode()
    new = policy_project.required_agreements.get(key="ai").version
    assert f'href="/agreements/{old.pk}/">Version' in history
    assert f'href="/agreements/{new.pk}/">Version' in history
    assert old.short_commit not in history  # commits only in the technical details
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
        f"/project/{REPOSITORY}/",
        f"/project/{REPOSITORY}/pulls/{item.number}/",
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


def test_home_links_to_the_projects(client):
    page = client.get("/").content.decode()
    assert 'href="/projects/"' in page and 'href="/agreements/"' not in page


def test_public_pages_call_them_agreements(client, policy_project, alice):
    client.force_login(alice)
    for url, expected in [
        ("/", ">Browse projects</a>"),
        (f"/project/{REPOSITORY}/", ">Earlier versions</a>"),
        (
            f"/agreements/history/{REPOSITORY}/agreements/ai-policy.md/",
            "The versions of this agreement",
        ),
    ]:
        response = client.get(url)
        assert response.status_code == 200
        page = response.content.decode()
        assert expected in page
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


def test_the_projects_page_shows_the_status_and_the_agreements(client, policy_project):
    page = client.get("/projects/").content.decode()
    project = page.split(f'data-project="{REPOSITORY}"')[1].split("</details>")[0]
    assert 'data-status="working"' in project
    for agreement in policy_project.required_agreements.all():
        assert f'href="/agreements/{agreement.version_id}/">{agreement.title}</a>' in project
    assert 'href="/projects/PyCalendar/">PyCalendar</a>' in page  # the organization
    assert f'href="/project/{REPOSITORY}/">' in project


def test_a_project_with_an_error_shows_it(client, policy_project):
    policy_project.error_code = "ConfigFileNotFound"
    policy_project.error_detail = ".github/agreements.yml"
    policy_project.save()
    page = client.get("/projects/").content.decode()
    project = page.split(f'data-project="{REPOSITORY}"')[1].split("</details>")[0]
    assert 'data-status="error"' in project
    assert "The repository has no configuration file" in project  # the title, on hover


def test_projects_are_grouped_by_organization(client, policy_project):
    page = client.get("/projects/").content.decode()
    owner = page.split('data-owner="PyCalendar"')[1].split("</details></li>\n</ul>")[0]
    assert f'data-project="{REPOSITORY}"' in owner
    assert "1 project" in page


def test_no_projects_says_how_to_add_one(client, db):
    page = client.get("/projects/").content.decode()
    assert "data-no-projects" in page and 'href="/setup/">Setup</a>' in page


def test_the_contributor_page_shows_valid_and_outdated_signatures(
    client, github, repository, alice
):
    from ai_pycal.services.repository_sync import RepositorySync
    from tests.conftest import sign_agreement

    cla = repository.required_agreements.get(key="cla")
    ai = repository.required_agreements.get(key="ai-policy")
    client.force_login(alice)
    sign_agreement(client, cla.version_id, "alice")
    sign_agreement(client, ai.version_id, "alice")
    github.push(REPOSITORY, {"agreements/cla.md": "# Contributor License Agreement\n\nNew."})
    RepositorySync(repository).sync()
    page = client.get("/contributor/alice/").content.decode()
    states = re.findall(r'data-signature-state="(\w+)"', page)
    assert states == ["outdated", "valid"]  # outdated first, one entry per agreement
    valid = page.split('data-signature-state="valid"')[1].split("</section>")[0]
    assert "valid-check" in valid and "data-technical" in valid
    outdated = page.split('data-signature-state="outdated"')[1].split("</section>")[0]
    assert "Outdated signature" in outdated and "valid-check" not in outdated
    title = page.split("data-title>")[1].split("</div>")[0]
    assert 'href="https://github.com/alice"' in title
    assert "Profile and email preferences" not in page
    assert "Projects engaged with" not in page
    assert "Defaults for future pull requests" not in page  # nothing chosen: no section


def test_mandatory_or_optional_is_kept_per_version(client, github, repository):
    from ai_pycal.models import AgreementUse
    from ai_pycal.services.repository_sync import RepositorySync

    old = repository.required_agreements.get(key="ai-policy").version
    assert AgreementUse.objects.get(repository=repository, version=old).mandatory
    config = (github.repositories[REPOSITORY].trees[github.repositories[REPOSITORY].refs["main"]])[
        ".github/agreements.yml"
    ].decode()
    github.push(
        REPOSITORY,
        {
            ".github/agreements.yml": config.replace("mandatory: true", "mandatory: false", 1),
            "agreements/ai-policy.md": "# AI Policy (example)\n\nNew version, now optional.",
        },
    )
    RepositorySync(repository).sync()
    new = repository.required_agreements.get(key="ai-policy").version
    assert not AgreementUse.objects.get(repository=repository, version=new).mandatory
    page = client.get(f"/agreements/history/{REPOSITORY}/agreements/ai-policy.md/").content.decode()
    newer = page.split(f'data-version-row="{new.pk}"')[1].split("</section>")[0]
    older = page.split(f'data-version-row="{old.pk}"')[1].split("</section>")[0]
    assert "Optional" in newer and "current" in newer
    assert "Mandatory" in older and "current" not in older


def test_the_projects_page_shows_all_projects_open(client, repository):
    from ai_pycal.models import Installation, Repository

    other = Installation.objects.create(github_id=2, account_login="other")
    Repository.objects.create(installation=other, github_id=77, full_name="other/x", active=True)
    page = client.get("/projects/").content.decode()
    assert '<details class="owner" open data-owner="PyCalendar">' in page
    assert '<details class="owner" open data-owner="other">' in page


def test_visitors_learn_that_private_projects_need_signing_in(client, repository, alice):
    repository.private = True
    repository.save()
    page = client.get("/projects/").content.decode()
    assert "data-no-projects" in page and "data-private-hint" in page
    assert 'href="/accounts/login/?next=/projects/"' in page
    client.force_login(alice)
    assert "data-private-hint" not in client.get("/projects/").content.decode()
