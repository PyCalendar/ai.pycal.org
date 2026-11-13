"""Only a person on the page of an agreement can sign it."""

import time

import pytest
from django.core import signing

from ai_pycal.models import RequiredAgreement, Signature
from ai_pycal.services.signer import SALT
from tests.conftest import ALICE, BOB, shown_token, sign_agreement

pytestmark = pytest.mark.django_db


@pytest.fixture
def cla(repository):
    return RequiredAgreement.objects.get(repository=repository, key="cla").version


def error_of(response) -> str:
    text = response.content.decode()
    return text.split('data-error="')[1].split('"')[0]


def test_the_agreement_is_shown_as_markdown(client, cla, alice):
    client.force_login(alice)
    page = client.get(f"/agreements/{cla.pk}/").content.decode()
    assert "<strong>" in page  # Markdown, rendered
    assert "<h1>Contributor License Agreement (example)</h1>" not in page  # shown once
    assert "I have read and accept this agreement." in page
    assert f"https://github.com/{cla.source}/blob/{cla.commit}/agreements/cla.md" in page


def test_visitors_are_asked_to_sign_in(client, cla):
    page = client.get(f"/agreements/{cla.pk}/").content.decode()
    assert "Sign in with GitHub to sign" in page
    assert 'name="shown"' not in page


def test_signing_needs_a_sign_in(client, cla):
    response = client.post(f"/agreements/{cla.pk}/sign/", {"accept": "yes", "handle": "alice"})
    assert response.status_code == 302
    assert response["Location"].startswith("/accounts/login/")
    assert not Signature.objects.exists()


def test_a_signature(client, cla, alice):
    client.force_login(alice)
    sign_agreement(client, cla.pk, "alice")
    signature = Signature.objects.get()
    assert (signature.github_id, signature.login, signature.version) == (ALICE[0], "alice", cla)
    page = client.get(f"/agreements/{cla.pk}/").content.decode()
    assert "data-signed" in page and 'name="shown"' not in page


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"accept": False}, "NotAccepted"),
        ({"handle": "bob"}, "HandleMismatch"),
        ({"handle": ""}, "HandleMismatch"),
        ({"token": ""}, "AgreementNotShown"),
        ({"token": "forged"}, "AgreementNotShown"),
    ],
)
def test_signing_needs_the_box_the_handle_and_the_page(client, cla, alice, kwargs, error):
    client.force_login(alice)
    response = sign_agreement(client, cla.pk, kwargs.pop("handle", "alice"), **kwargs)
    assert response.status_code == 400
    assert error_of(response) == error
    assert f"#ai_pycal.errors.signing.{error}" in response.content.decode()
    assert not Signature.objects.exists()


def test_the_page_of_one_person_does_not_sign_for_another(client, cla, alice, bob):
    client.force_login(alice)
    token = shown_token(client, cla.pk)
    client.force_login(bob)
    response = sign_agreement(client, cla.pk, "bob", token=token)
    assert error_of(response) == "AgreementNotShown"


def test_the_page_of_one_agreement_does_not_sign_another(client, repository, cla, alice):
    other = RequiredAgreement.objects.get(repository=repository, key="ai-policy").version
    client.force_login(alice)
    response = sign_agreement(client, other.pk, "alice", token=shown_token(client, cla.pk))
    assert error_of(response) == "AgreementNotShown"


def test_signing_too_fast(client, cla, alice, settings):
    settings.SIGN_MIN_SECONDS = 60
    client.force_login(alice)
    assert error_of(sign_agreement(client, cla.pk, "alice")) == "SignedTooFast"


def test_an_old_page_can_not_be_signed(client, cla, alice):
    client.force_login(alice)
    token = signing.dumps({"v": cla.pk, "g": ALICE[0], "t": time.time() - 25 * 3600}, salt=SALT)
    assert error_of(sign_agreement(client, cla.pk, "alice", token=token)) == "SigningExpired"


def test_versions_nobody_asks_for_can_not_be_signed(client, repository, cla, alice):
    client.force_login(alice)
    token = shown_token(client, cla.pk)
    repository.active = False
    repository.save()
    response = sign_agreement(client, cla.pk, "alice", token=token)
    assert response.status_code == 404
    assert error_of(response) == "AgreementVersionNotRequired"


def test_an_unknown_agreement(client, alice):
    client.force_login(alice)
    response = client.get("/agreements/999/")
    assert response.status_code == 404
    assert error_of(response) == "AgreementNotFound"


def test_my_agreements(client, github, repository, cla, alice):
    from tests.conftest import pull_payload, send_webhook

    send_webhook(client, "pull_request", pull_payload(github, 1))
    client.force_login(alice)
    page = client.get("/my-agreements/").content.decode()
    assert "AI Policy (example)" in page and "Contributor License Agreement (example)" in page
    sign_agreement(client, cla.pk, "alice")
    page = client.get("/my-agreements/").content.decode()
    assert page.count("data-to-sign=") == 1


def test_a_person_without_github_sees_a_warning(client, db, django_user_model):
    user = django_user_model.objects.create(username="local")
    client.force_login(user)
    assert "not connected to GitHub" in client.get("/my-agreements/").content.decode()


def test_people_are_identified_by_their_id_not_their_handle(client, cla, alice):
    client.force_login(alice)
    sign_agreement(client, cla.pk, "alice")
    alice.socialaccount_set.update(extra_data={"login": "alice-renamed"})
    assert "data-signed" in client.get(f"/agreements/{cla.pk}/").content.decode()
    assert Signature.objects.filter(github_id=ALICE[0]).count() == 1
    assert not Signature.objects.filter(github_id=BOB[0]).exists()


def test_the_admin_can_not_add_signatures(client, db, django_user_model):
    admin = django_user_model.objects.create(username="root", is_staff=True, is_superuser=True)
    client.force_login(admin)
    assert client.get("/admin/ai_pycal/signature/add/").status_code == 403
