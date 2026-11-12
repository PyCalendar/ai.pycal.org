"""A changed agreement needs a new signature, and shows what changed."""

import pytest

from ai_pycal.models import AgreementVersion, Installation, Repository, RequiredAgreement, Signature
from ai_pycal.services.repository_setup import RepositorySetup
from ai_pycal.services.repository_sync import RepositorySync
from tests.conftest import (
    DATA,
    REPOSITORY,
    pull_payload,
    send_webhook,
    sign_agreement,
)

pytestmark = pytest.mark.django_db
CHANGED = (
    (DATA / "cla.md")
    .read_text()
    .replace(
        "3. **No warranty.**", "3. **Patents.** I grant a patent license.\n4. **No warranty.**"
    )
)


def version_of(repository, key="cla") -> AgreementVersion:
    return RequiredAgreement.objects.get(repository=repository, key=key).version


def test_a_new_commit_of_the_agreement_needs_a_new_signature(client, github, repository, alice):
    send_webhook(client, "pull_request", pull_payload(github, 1))
    client.force_login(alice)
    old = version_of(repository)
    sign_agreement(client, old.pk, "alice")
    assert "cla-signed" in github.labels[(REPOSITORY, 1)]

    github.push(REPOSITORY, {"agreements/cla.md": CHANGED})
    payload = pull_payload(github, 1, action="synchronize")
    send_webhook(client, "pull_request", payload)

    new = version_of(repository)
    assert new.commit != old.commit and new.path == old.path
    assert "cla-signed" not in github.labels[(REPOSITORY, 1)]
    sha = payload["pull_request"]["head"]["sha"]
    assert github.status(REPOSITORY, sha, "ai.example.org/cla")["state"] == "pending"
    assert Signature.objects.filter(version=old).exists()  # the old signature stays


def test_the_changes_since_the_signature_are_shown(client, github, repository, alice):
    client.force_login(alice)
    old = version_of(repository)
    sign_agreement(client, old.pk, "alice")
    github.push(REPOSITORY, {"agreements/cla.md": CHANGED})
    RepositorySync(repository).sync()
    new = version_of(repository)

    page = client.get(f"/agreements/{new.pk}/").content.decode()
    assert "data-changes" in page and "data-signed-before" in page
    # the whole agreement first, the colored changes in the second tab
    assert '<input type="radio" name="view" id="view-agreement" checked>' in page
    assert page.index('id="agreement"') < page.index("data-changes")
    assert 'for="view-changes">Changes since you signed</label>' in page
    assert '<span class="diff-added">+ 3. **Patents.** I grant a patent license.</span>' in page
    assert '<span class="diff-removed">- 3. **No warranty.**' in page
    assert f"/agreements/{new.pk}/changes/{old.pk}/" in page

    page = client.get(f"/agreements/{new.pk}/changes/{old.pk}/").content.decode()
    assert "+ 4. **No warranty.**" in page

    sign_agreement(client, new.pk, "alice")
    assert Signature.objects.filter(github_id=42).count() == 2


def test_an_unrelated_commit_preserves_the_version_and_signature(client, github, repository, alice):
    """Only a commit changing the agreement file creates another version."""
    client.force_login(alice)
    old = version_of(repository)
    sign_agreement(client, old.pk, "alice")
    before = AgreementVersion.objects.count()
    head = github.push(REPOSITORY, {"README.md": "other file"})
    send_webhook(client, "pull_request", pull_payload(github, 1))
    new = version_of(repository)
    assert head != old.commit
    assert new.pk == old.pk and new.commit == old.commit
    assert AgreementVersion.objects.count() == before
    assert "cla-signed" in github.labels[(REPOSITORY, 1)]
    status = github.status(
        REPOSITORY, github.pulls[REPOSITORY][0]["head"]["sha"], "ai.example.org/cla"
    )
    assert status["state"] == "success"
    page = client.get(f"/agreements/{new.pk}/").content.decode()
    assert "data-signed" in page
    assert 'name="shown"' not in page


def test_a_tag_keeps_the_agreement_when_the_branch_changes(client, github, repository, alice):
    tagged = github.repositories[REPOSITORY].refs["main"]
    github.tag(REPOSITORY, "cla-v1", tagged)
    github.push(
        REPOSITORY,
        {
            ".github/agreements.yml": """
version: 1.0.0
agreements:
  cla: {name: CLA, tag: cla-v1, path: agreements/cla.md, pr: {tags: cla-signed}}
"""
        },
    )
    RepositorySync(repository).sync()
    first = version_of(repository)
    github.push(REPOSITORY, {"agreements/cla.md": CHANGED})
    RepositorySync(repository).sync()
    assert version_of(repository) == first
    assert first.commit == tagged


def test_the_same_agreement_in_two_repositories_is_signed_once(client, github, repository, alice):
    """Identified by commit and path: a central agreement used by several repositories."""
    other = "PyCalendar/icalendar"
    github.push(
        other,
        {
            ".github/agreements.yml": f"""
version: 1.0.0
agreements:
  contributor-agreement:
    name: The CLA of all repositories
    tag: {github.repositories[REPOSITORY].refs["main"]}
    repository: https://github.com/{REPOSITORY}
    path: agreements/cla.md
    pr:
      tags: cla
"""
        },
    )
    github.installation_repositories[1].append(other)
    second = Repository.objects.create(
        installation=Installation.objects.get(github_id=1),
        github_id=github.repositories[other].id,
        full_name=other,
    )
    RepositorySetup(second).add()
    assert version_of(second, "contributor-agreement") == version_of(repository)

    send_webhook(client, "pull_request", pull_payload(github, 1))
    send_webhook(client, "pull_request", pull_payload(github, 7, repo=other))
    client.force_login(alice)
    sign_agreement(client, version_of(repository).pk, "alice")
    assert "cla-signed" in github.labels[(REPOSITORY, 1)]
    assert github.labels[(other, 7)] == ["cla"]
    assert AgreementVersion.objects.filter(path="agreements/cla.md").count() == 1


def test_the_same_path_in_another_commit_is_another_agreement(client, github, repository, alice):
    other = "PyCalendar/other"
    github.push(
        other,
        {
            ".github/agreements.yml": "version: 1.0.0\nagreements:\n  cla: {name: CLA, path: agreements/cla.md, pr: {tags: cla}}\n",
            "agreements/cla.md": "Another CLA",
        },
    )
    github.installation_repositories[1].append(other)
    second = Repository.objects.create(
        installation=Installation.objects.get(github_id=1),
        github_id=github.repositories[other].id,
        full_name=other,
    )
    RepositorySetup(second).add()
    assert version_of(second) != version_of(repository)
    assert version_of(second).text == "Another CLA"


@pytest.mark.parametrize("ref_kind", ["branch", "tag", "commit"])
def test_version_is_the_last_file_edit_before_the_selected_ref(
    client, github, repository, ref_kind
):
    original = version_of(repository)
    snapshot = github.push(REPOSITORY, {"README.md": "first unrelated change"})
    if ref_kind == "branch":
        ref = "stable/policies"
        github.tag(REPOSITORY, ref, snapshot)
    elif ref_kind == "tag":
        ref = "policy-v1"
        github.tag(REPOSITORY, ref, snapshot)
    else:
        ref = snapshot
    github.push(REPOSITORY, {"agreements/cla.md": CHANGED})
    github.push(
        REPOSITORY,
        {
            ".github/agreements.yml": f"""version: 2.0.0
agreements:
  cla:
    name: CLA
    ref: {ref}
    path: agreements/cla.md
    pr: {{labels: cla-signed}}
"""
        },
    )
    RepositorySync(repository).sync()
    assert version_of(repository).pk == original.pk
    assert version_of(repository).commit == original.commit
    history = [
        r
        for r in github.requests
        if r.url.path.endswith("/commits") and r.url.params.get("path") == "agreements/cla.md"
    ][-1]
    assert history.url.params["sha"] == snapshot
    assert history.url.params["per_page"] == "1"


def test_each_file_has_its_own_last_edit(client, github, repository):
    ai_before = version_of(repository, "ai-policy")
    cla_before = version_of(repository, "cla")
    edit = github.push(REPOSITORY, {"agreements/cla.md": CHANGED})
    head = github.push(REPOSITORY, {"README.md": "later unrelated commit"})
    RepositorySync(repository).sync()
    assert version_of(repository, "ai-policy").pk == ai_before.pk
    assert version_of(repository).commit == edit
    assert version_of(repository).commit != head
    assert version_of(repository).pk != cla_before.pk


def test_a_revert_is_a_new_file_edit_even_when_text_matches_old_version(client, github, repository):
    original = version_of(repository)
    github.push(REPOSITORY, {"agreements/cla.md": CHANGED})
    RepositorySync(repository).sync()
    revert = github.push(REPOSITORY, {"agreements/cla.md": original.text})
    github.push(REPOSITORY, {"README.md": "unrelated commit after revert"})
    RepositorySync(repository).sync()
    current = version_of(repository)
    assert current.commit == revert
    assert current.pk != original.pk
    assert current.text == original.text


def test_a_missing_or_deleted_file_never_falls_back_to_its_previous_text(github, repository):
    from ai_pycal.errors import AgreementFileNotFound

    github.push(REPOSITORY, {"agreements/cla.md": None})
    github.push(REPOSITORY, {"README.md": "unrelated commit after deletion"})
    with pytest.raises(AgreementFileNotFound):
        RepositorySync(repository).sync()


def test_ref_is_pinned_before_the_branch_moves(github, repository, monkeypatch):
    import httpx

    from ai_pycal.github import client as module

    original = version_of(repository)
    handler = github.handle
    moved = False
    resolutions = 0

    def move_after_resolve(request):
        nonlocal moved, resolutions
        response = handler(request)
        if request.url.path.endswith("/commits/main"):
            resolutions += 1
            if resolutions == 2:
                moved = True
                github.push(REPOSITORY, {"agreements/cla.md": CHANGED})
        return response

    monkeypatch.setattr(module, "TRANSPORT", httpx.MockTransport(move_after_resolve))
    RepositorySync(repository).sync()
    assert moved
    assert version_of(repository).pk == original.pk
