"""Fixtures: a fake GitHub, a GitHub App with a key, people and repositories."""

import json
import re
from pathlib import Path

import pytest
from allauth.socialaccount.models import SocialAccount, SocialToken
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.contrib.auth import get_user_model

from ai_pycal.github import client as github_client
from ai_pycal.github.app import GitHubApp
from ai_pycal.github.webhook_signature import sign
from ai_pycal.models import Installation, Repository
from ai_pycal.services.repository_setup import RepositorySetup
from tests.fakes.github import FakeGitHub

DATA = Path(__file__).parent / "data"
EXAMPLE = Path(__file__).parent.parent / "example"
WEBHOOK_SECRET = "webhook-secret"
ALICE = (42, "alice")
BOB = (43, "bob")
MAINTAINER = (7, "maintainer")
REPOSITORY = "PyCalendar/sign.pycal.org-example"


@pytest.fixture(scope="session")
def private_key() -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode()


@pytest.fixture(autouse=True)
def app_settings(settings, private_key):
    settings.GITHUB_APP_ID = "1"
    settings.GITHUB_APP_SLUG = "ai-pycal-test"
    settings.GITHUB_APP_PRIVATE_KEY = private_key
    settings.GITHUB_WEBHOOK_SECRET = WEBHOOK_SECRET
    settings.SITE_URL = "https://ai.example.org"
    settings.STATUS_CONTEXT = "ai.example.org"
    settings.SIGN_MIN_SECONDS = 0
    settings.SOCIALACCOUNT_PROVIDERS = {
        "github": {"SCOPE": [], "APP": {"client_id": "client", "secret": "secret"}}
    }
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    return settings


@pytest.fixture(autouse=True)
def github(monkeypatch) -> FakeGitHub:
    """The fake GitHub that answers all requests of the site."""
    fake = FakeGitHub()
    monkeypatch.setattr(github_client, "TRANSPORT", fake.transport())
    GitHubApp.forget_tokens()
    yield fake
    GitHubApp.forget_tokens()


def agreement_files() -> dict[str, str]:
    return {
        ".github/agreements.yml": (DATA / "agreements.yml").read_text(),
        "agreements/ai-policy.md": (DATA / "ai-policy.md").read_text(),
        "agreements/cla.md": (DATA / "cla.md").read_text(),
    }


def person(github_id: int, login: str, token: str = ""):
    user = get_user_model().objects.create(username=login)
    account = SocialAccount.objects.create(
        user=user, provider="github", uid=str(github_id), extra_data={"login": login}
    )
    if token:
        SocialToken.objects.create(account=account, token=token)
    return user


@pytest.fixture
def alice(db):
    return person(*ALICE)


@pytest.fixture
def bob(db):
    return person(*BOB)


@pytest.fixture
def maintainer(db):
    return person(*MAINTAINER, token="user-token")


@pytest.fixture
def example(github) -> FakeGitHub:
    """The example repository on GitHub with the app installed, not yet added."""
    github.push(REPOSITORY, agreement_files())
    github.install(1, "PyCalendar", [REPOSITORY])
    github.user_installations.append(1)
    return github


@pytest.fixture
def repository(example, db) -> Repository:
    """The example repository, added to the site."""
    installation = Installation.objects.create(
        github_id=1,
        account_login="PyCalendar",
        account_type="Organization",
        permissions=example.installations[1]["permissions"],
    )
    repo = Repository.objects.create(
        installation=installation,
        github_id=example.repositories[REPOSITORY].id,
        full_name=REPOSITORY,
    )
    RepositorySetup(repo).add()
    repo.refresh_from_db()
    return repo


def send_webhook(client, event: str, payload: dict, secret: str = WEBHOOK_SECRET):
    body = json.dumps(payload).encode()
    headers = {"HTTP_X_GITHUB_EVENT": event}
    if secret is not None:
        headers["HTTP_X_HUB_SIGNATURE_256"] = sign(secret, body)
    return client.post("/github/webhook/", body, content_type="application/json", **headers)


def pull_payload(github: FakeGitHub, number: int, author=ALICE, action="opened", repo=REPOSITORY):
    data = next(
        (p for p in github.pulls.get(repo, []) if p["number"] == number), None
    ) or github.open_pull(repo, number, author)
    return {
        "action": action,
        "pull_request": data,
        "repository": github.repositories[repo].as_json(),
        "installation": {"id": 1},
    }


def shown_token(client, version_pk: int) -> str:
    page = client.get(f"/agreements/{version_pk}/").content.decode()
    return re.search(r'name="shown" value="([^"]+)"', page).group(1)


def sign_agreement(client, version_pk: int, handle: str, accept: bool = True, token=None, **extra):
    data = {
        "shown": shown_token(client, version_pk) if token is None else token,
        "handle": handle,
        **({"accept": "yes"} if accept else {}),
        **extra,
    }
    return client.post(f"/agreements/{version_pk}/sign/", data)
