"""The pages of the site and signing in with GitHub only."""

import pytest
from django.contrib.auth import get_user_model

from tests.conftest import person

pytestmark = pytest.mark.django_db


def test_the_start_page(client):
    page = client.get("/").content.decode()
    assert "Agreements for pull requests" in page
    assert "Sign in with GitHub" in page
    assert "https://docs.sign.pycal.org/" in page


def test_sign_in_without_an_app_offers_to_register_it(client, settings):
    """Without a GitHub App, as on a new site, the sign-in page offers to register it.

    Signing in needs only the OAuth app, so the button stays.
    """
    settings.GITHUB_APP_ID = ""
    response = client.get("/accounts/login/")
    page = response.content.decode()
    assert response.status_code == 200
    assert "This site has no GitHub App yet" in page
    assert 'href="/setup/github-app/">Register GitHub App</a>' in page
    assert 'action="/accounts/github/login/' in page


def test_signing_in_without_client_explains_the_setup(client, settings):
    """A sign-in sent without the OAuth app shows the error, its details and the guide."""
    settings.SIGN_IN_WITH_OAUTH_APP = False
    settings.SOCIALACCOUNT_PROVIDERS = {"github": {"SCOPE": ["user:email"]}}
    response = client.post("/accounts/github/login/")
    page = response.content.decode()
    assert response.status_code == 503
    assert "Signing in with GitHub is not configured" in page
    assert "GITHUB_OAUTH_CLIENT_ID" in page
    assert "errors.html#ai_pycal.errors.github.SignInNotConfigured" in page
    assert "how-to/github-app-site.html#oauth-app" in page
    details = page.split('id="error-details"')[1].split("</textarea>")[0]
    assert "Error: SignInNotConfigured (HTTP 503)" in details
    assert "Page: /accounts/github/login/" in details


def test_health(client):
    assert client.get("/health/").json() == {"status": "ok"}


def test_sign_in_is_with_github_only(client):
    page = client.get("/accounts/login/").content.decode()
    assert 'action="/accounts/github/login/' in page
    assert 'type="password"' not in page
    assert (
        client.get("/accounts/signup/").status_code in (302, 404)
        or b"password" not in client.get("/accounts/signup/").content
    )


def test_site_admins_administer(settings):
    from allauth.account.signals import user_logged_in

    settings.SITE_ADMINS = ["maintainer"]
    admin = person(1, "Maintainer")
    other = person(2, "other")
    for user in (admin, other):
        user_logged_in.send(sender=get_user_model(), request=None, user=user)
        user.refresh_from_db()
    assert admin.is_staff and admin.is_superuser
    assert not other.is_staff


def test_pages_can_not_be_framed(client):
    assert client.get("/").headers["X-Frame-Options"] == "DENY"


@pytest.mark.parametrize("url", ["http://localhost:8000/", "https://docs.example/preview"])
def test_documentation_navigation_and_error_help_share_the_configured_url(client, settings, url):
    settings.DOCS_URL = url
    base = url.rstrip("/") + "/"
    page = client.get("/about/").content.decode()
    assert f'href="{base}"' in page
    assert f'href="{base}changelog.html"' in page
    settings.SIGN_IN_WITH_OAUTH_APP = False
    settings.SOCIALACCOUNT_PROVIDERS = {"github": {"SCOPE": ["user:email"]}}
    response = client.post("/accounts/github/login/")
    assert response.status_code == 503
    page = response.content.decode()
    assert f"{base}reference/errors.html#ai_pycal.errors.github.SignInNotConfigured" in page
    assert f"{base}how-to/github-app-site.html#oauth-app" in page


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("/{name}/", "/project/{name}/"),
        ("/{name}/pull/3/", "/project/{name}/pulls/3/"),
        ("/{name}/?x=1", "/project/{name}/?x=1"),
        ("/repository/{name}/", "/project/{name}/"),
        ("/repository/{name}/pull/3/", "/project/{name}/pulls/3/"),
    ],
)
def test_the_older_repository_addresses_redirect(client, repository, old, new):
    name = repository.full_name
    response = client.get(old.format(name=name))
    assert response.status_code == 301
    assert response["Location"] == new.format(name=name)


@pytest.mark.parametrize("page", ["/accounts/signup/", "/nobody/nothing/", "/a/b/pull/1/"])
def test_other_addresses_of_two_parts_are_not_found(client, page):
    assert client.get(page).status_code == 404


def test_the_start_names_site_admins_without_an_account(settings, capsys, db):
    from django.core.management import call_command

    person(1, "niccokunzmann")
    settings.SITE_ADMINS = ["nicokunzmann", "niccokunzmann"]
    call_command("prepare")
    out = capsys.readouterr().out
    assert "SITE_ADMINS without an account on this site" in out
    assert "nicokunzmann" in out.split("SITE_ADMINS without")[1].split("\n")[0]
    assert "niccokunzmann" not in out.split("SITE_ADMINS without")[1].split("\n")[0]


@pytest.mark.parametrize(
    "url",
    [
        "/",
        "/projects/",
        "/projects/PyCalendar/",
        "/about/",
        "/licenses/",
        "/contributor/alice/",
        "/logs/PyCalendar/",
    ],
)
def test_public_pages_need_no_sign_in(client, url, db):
    assert client.get(url).status_code == 200


def test_public_pages_of_a_project_need_no_sign_in(client, repository):
    from tests.conftest import REPOSITORY

    cla = repository.required_agreements.get(key="cla")
    for url in (
        f"/project/{REPOSITORY}/",
        f"/logs/{REPOSITORY}/",
        f"/agreements/{cla.version_id}/",
    ):
        assert client.get(url).status_code == 200, url


@pytest.mark.parametrize("url", ["/my-agreements/", "/todos/", "/profile/", "/setup/"])
def test_personal_pages_ask_to_sign_in(client, url, db):
    response = client.get(url)
    assert response.status_code == 302 and response["Location"].startswith("/accounts/login/")


def test_the_start_page_counts_only_visible_projects(client, repository):
    repository.private = True
    repository.save()
    assert "0 repositories" in client.get("/").content.decode()
    repository.private = False
    repository.save()
    assert "1 repository" in client.get("/").content.decode()
