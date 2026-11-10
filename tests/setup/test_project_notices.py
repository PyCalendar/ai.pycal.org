"""Actionable project problems, verified emails and private profile preferences."""

import pytest
from allauth.account.models import EmailAddress, EmailConfirmationHMAC

from ai_pycal.errors import AgreementFileNotFound, CannotWriteLabels
from ai_pycal.models import Profile, ProjectProblem
from ai_pycal.services.project_notices import ProjectNotices
from ai_pycal.services.repository_sync import RepositorySync
from tests.conftest import REPOSITORY

pytestmark = pytest.mark.django_db


@pytest.fixture
def maintainer_email(repository, maintainer):
    repository.watchers.add(maintainer)
    return EmailAddress.objects.create(
        user=maintainer, email="maintainer@example.org", verified=True, primary=True
    )


def test_invalid_setup_emails_once_and_appears_in_messages(
    client, github, repository, maintainer, maintainer_email, mailoutbox
):
    github.push(REPOSITORY, {"agreements/cla.md": None})
    with pytest.raises(AgreementFileNotFound):
        RepositorySync(repository).sync()
    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == [maintainer_email.email]
    assert "AgreementFileNotFound" in mailoutbox[0].body
    with pytest.raises(AgreementFileNotFound):
        RepositorySync(repository).sync()
    assert len(mailoutbox) == 1
    client.force_login(maintainer)
    page = client.get("/profile/").content.decode()
    assert "How to resolve" in page and "file of an agreement does not exist" in page
    github.push(REPOSITORY, {"agreements/cla.md": "# Fixed CLA"})
    RepositorySync(repository).sync()
    assert not ProjectProblem.objects.filter(active=True).exists()
    github.push(REPOSITORY, {"agreements/cla.md": None})
    with pytest.raises(AgreementFileNotFound):
        RepositorySync(repository).sync()
    assert len(mailoutbox) == 2


def test_opt_out_and_unverified_addresses_do_not_receive_problem_email(
    client, repository, maintainer, maintainer_email, mailoutbox
):
    client.force_login(maintainer)
    assert client.post("/profile/", {}).status_code == 302
    ProjectNotices(repository).record(CannotWriteLabels("permission missing"))
    assert mailoutbox == []
    assert ProjectProblem.objects.get().active  # Opting out keeps in-app messages.
    Profile.objects.filter(user=maintainer).update(email_notifications=True)
    maintainer_email.verified = False
    maintainer_email.save()
    ProjectNotices(repository).record(CannotWriteLabels("permission missing"))
    assert mailoutbox == []
    maintainer_email.verified = True
    maintainer_email.save()
    ProjectNotices(repository).record(CannotWriteLabels("permission missing"))
    assert len(mailoutbox) == 1


def test_email_delivery_failure_preserves_problem_for_retry(
    repository, maintainer_email, monkeypatch, mailoutbox
):
    def fail(*args, **kwargs):
        raise OSError("mail unavailable")

    with monkeypatch.context() as patch:
        patch.setattr("ai_pycal.services.project_notices.send_mail", fail)
        ProjectNotices(repository).record(CannotWriteLabels("missing permission"))
    assert not ProjectProblem.objects.get().notified
    ProjectNotices(repository).record(CannotWriteLabels("missing permission"))
    assert len(mailoutbox) == 1


def test_profile_email_management_and_verification(client, maintainer, mailoutbox):
    client.force_login(maintainer)
    assert client.get("/profile/").status_code == 200
    assert client.get("/accounts/email/").status_code == 200
    response = client.post("/accounts/email/", {"email": "new@example.org", "action_add": ""})
    assert response.status_code == 302
    address = EmailAddress.objects.get(user=maintainer, email="new@example.org")
    assert not address.verified
    assert len(mailoutbox) == 1
    key = EmailConfirmationHMAC(address).key
    response = client.post(f"/accounts/confirm-email/{key}/")
    assert response.status_code == 302
    address.refresh_from_db()
    assert address.verified
    assert client.get("/accounts/signup/").status_code == 404
    assert client.get("/accounts/password/set/").status_code == 404


def test_profile_is_private_and_discovers_write_projects(client, repository, maintainer, github):
    assert client.get("/profile/").status_code == 302
    github.user_roles[REPOSITORY] = {"push": True}
    client.force_login(maintainer)
    page = client.get("/profile/").content.decode()
    assert REPOSITORY in page
    assert repository.watchers.filter(pk=maintainer.pk).exists()
    client.logout()
    page = client.get("/contributor/maintainer/").content.decode()
    assert "Email preferences" not in page


def test_label_failure_has_specific_error_email_and_resolution(
    client, repository, maintainer_email, github, mailoutbox, monkeypatch
):
    import httpx

    from ai_pycal.github import client as module
    from tests.conftest import pull_payload, send_webhook

    original = github.handle

    def denied(request):
        if request.method == "GET" and request.url.path.endswith("/labels"):
            return httpx.Response(403, json={"message": "Resource not accessible by integration"})
        return original(request)

    monkeypatch.setattr(module, "TRANSPORT", httpx.MockTransport(denied))
    response = send_webhook(client, "pull_request", pull_payload(github, 1))
    assert response.json()["error"] == "CannotWriteLabels"
    assert len(mailoutbox) == 1
    assert ProjectProblem.objects.get(code="CannotWriteLabels").active
    monkeypatch.setattr(module, "TRANSPORT", github.transport())
    response = send_webhook(client, "pull_request", pull_payload(github, 1))
    assert response.status_code == 200
    assert not ProjectProblem.objects.get(code="CannotWriteLabels").active
