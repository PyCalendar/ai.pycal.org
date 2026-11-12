"""Administrators install the GitHub App and add repositories with a configuration file."""

import pytest

from ai_pycal.models import Installation, Repository
from tests.conftest import REPOSITORY

pytestmark = pytest.mark.django_db


def error_of(response) -> str:
    return response.content.decode().split('data-error="')[1].split('"')[0]


def test_the_setup_needs_a_sign_in(client):
    assert client.get("/setup/").status_code == 302


def test_the_setup_page_is_a_tutorial_with_the_install_link(client, example, maintainer):
    client.force_login(maintainer)
    page = client.get("/setup/").content.decode()
    assert "https://github.com/apps/ai-pycal-test/installations/new" in page
    assert ".github/agreements.yml" in page
    assert "pull_requests: write" in page and "statuses: write" in page
    assert REPOSITORY in page and ">Add<" in page


def test_github_sends_administrators_back_after_installing(client, example, maintainer):
    client.force_login(maintainer)
    response = client.get("/setup/installed/?installation_id=1&setup_action=install")
    assert response.status_code == 302
    installation = Installation.objects.get(github_id=1)
    assert list(installation.admins.all()) == [maintainer]


def test_an_installation_of_someone_else(client, example, maintainer):
    example.install(2, "other", [])
    client.force_login(maintainer)
    response = client.get("/setup/installed/?installation_id=2")
    assert response.status_code == 403
    assert error_of(response) == "InstallationNotYours"


def test_an_expired_sign_in(client, example, maintainer):
    maintainer.socialaccount_set.get().socialtoken_set.update(token="expired")
    client.force_login(maintainer)
    response = client.get("/setup/installed/?installation_id=1")
    assert response.status_code == 401
    assert error_of(response) == "GitHubLoginExpired"
    page = client.get("/setup/").content.decode()
    assert 'data-error="GitHubLoginExpired"' in page


def test_contributors_without_a_token_see_the_tutorial(client, example, alice):
    client.force_login(alice)
    page = client.get("/setup/").content.decode()
    assert 'data-error="GitHubLoginExpired"' in page


def test_adding_a_repository(client, example, maintainer):
    client.force_login(maintainer)
    repo_id = example.repositories[REPOSITORY].id
    response = client.post(f"/setup/1/{repo_id}/add/")
    assert response.status_code == 302
    repository = Repository.objects.get(github_id=repo_id)
    assert repository.active
    assert repository.config_version == "2.1.0"
    assert [a.key for a in repository.required_agreements.all()] == ["ai-policy", "cla"]
    page = client.get(f"/repository/{REPOSITORY}/").content.decode()
    assert "AI Policy (example)" in page and "cla-signed" in page


def test_a_repository_without_a_configuration_can_not_be_added(client, example, maintainer):
    example.push(REPOSITORY, {".github/agreements.yml": None})
    client.force_login(maintainer)
    response = client.post(f"/setup/1/{example.repositories[REPOSITORY].id}/add/")
    assert response.status_code == 404
    assert error_of(response) == "ConfigFileNotFound"
    text = response.content.decode()
    assert "reference/errors.html#ai_pycal.errors.config_file.ConfigFileNotFound" in text
    assert "reference/config-file.html" in text
    assert not Repository.objects.get().active


@pytest.mark.parametrize(
    ("files", "error"),
    [
        ({"agreements/cla.md": None}, "AgreementFileNotFound"),
        ({"agreements/cla.md": b"\xff\xfe"}, "AgreementFileNotText"),
        ({"agreements/cla.md": "x" * 200_001}, "AgreementFileTooLarge"),
        (
            {
                ".github/agreements.yml": "version: 1.0.0\nagreements:\n  a: {name: A, tag: v9, path: a.md, pr: {tags: a}}\n"
            },
            "AgreementRefNotFound",
        ),
        (
            {
                ".github/agreements.yml": "version: 1.0.0\nagreements:\n  a: {name: A, repository: PyCalendar/private, path: a.md, pr: {tags: a}}\n"
            },
            "AgreementRefNotFound",
        ),
    ],
)
def test_agreements_that_can_not_be_read(client, example, maintainer, files, error):
    example.repository("PyCalendar/private", private=True)
    example.push("PyCalendar/private", {"a.md": "secret"})
    example.push(REPOSITORY, files)
    client.force_login(maintainer)
    response = client.post(f"/setup/1/{example.repositories[REPOSITORY].id}/add/")
    assert error_of(response) == error


def test_only_administrators_of_the_repository_can_add_it(client, example, maintainer):
    example.user_roles[REPOSITORY] = {"push": True}
    client.force_login(maintainer)
    assert "needs the role admin or maintain" in client.get("/setup/").content.decode()
    response = client.post(f"/setup/1/{example.repositories[REPOSITORY].id}/add/")
    assert response.status_code == 403
    assert error_of(response) == "NotRepositoryAdmin"


def test_removing_a_repository(client, repository, maintainer):
    client.force_login(maintainer)
    client.post(f"/setup/1/{repository.github_id}/remove/")
    repository.refresh_from_db()
    assert not repository.active


def test_the_email_for_permissions(client, example, maintainer):
    client.force_login(maintainer)
    client.post("/setup/1/email/", {"email": "maintainers@example.org"})
    assert Installation.objects.get(github_id=1).notify_email == "maintainers@example.org"
    response = client.post("/setup/1/email/", {"email": "no address"})
    assert error_of(response) == "InvalidNotificationEmail"


def test_an_unknown_repository(client, db):
    assert client.get("/nobody/nothing/").status_code == 404  # the older address
    response = client.get("/repository/nobody/nothing/")
    assert response.status_code == 404
    assert error_of(response) == "RepositoryNotFound"


def test_without_a_github_app(client, settings, maintainer):
    settings.GITHUB_APP_ID = ""
    client.force_login(maintainer)
    assert "This site has no GitHub App yet." in client.get("/setup/").content.decode()


def test_unconfigured_setup_links_to_common_page_and_three_flows(client, settings, maintainer):
    settings.GITHUB_APP_ID = ""
    settings.DOCS_URL = "http://localhost:8000/"
    client.force_login(maintainer)
    page = client.get("/setup/").content.decode()
    assert "Choose a GitHub App setup flow" in page
    assert 'href="http://localhost:8000/how-to/github-app.html"' in page
    register = page.index('href="/setup/github-app/">Register GitHub App</a>')
    form = page.index("App manifest with the submission form")
    cli = page.index("App manifest CLI flow")
    manual = page.index("Manual app creation")
    assert register < form < cli < manual
    assert 'href="http://localhost:8000/how-to/github-app-manifest.html"' in page
    assert 'href="http://localhost:8000/how-to/github-app-manual.html"' in page
    assert 'href="http://localhost:8000/how-to/create-github-app.html"' in page


def test_unconfigured_setup_shows_env_settings_without_credentials(client, settings, maintainer):
    settings.GITHUB_APP_ID = ""
    settings.GITHUB_WEBHOOK_SECRET = "do-not-show-this-secret"
    client.force_login(maintainer)
    page = client.get("/setup/").content.decode()
    assert ".env.development.example" in page
    assert "reads <code>.env</code> automatically" in page
    assert "restart it after editing" in page
    for variable in (
        "GITHUB_APP_ID",
        "GITHUB_APP_SLUG",
        "GITHUB_CLIENT_ID",
        "GITHUB_SECRET",
        "GITHUB_WEBHOOK_SECRET",
        "GITHUB_APP_PRIVATE_KEY_FILE",
    ):
        assert f"{variable}=" in page
    assert "data/github-app.pem" in page
    assert "do-not-show-this-secret" not in page
    assert settings.GITHUB_APP_PRIVATE_KEY not in page


def test_the_return_after_an_installation_goes_to_the_setup(client):
    """With OAuth during installation, GitHub returns to the sign-in callback without state."""
    response = client.get(
        "/accounts/github/login/callback/"
        "?code=one-time&installation_id=181305674&setup_action=install"
    )
    assert response.status_code == 302
    assert (
        response["Location"] == "/setup/installed/?installation_id=181305674&setup_action=install"
    )
    assert "code" not in response["Location"]


def test_a_sign_in_callback_is_still_handled_by_allauth(client):
    response = client.get("/accounts/github/login/callback/?code=x&state=y")
    assert "/setup/installed/" not in response.get("Location", "")
    assert b"Third-Party Login Failure" in response.content or response.status_code != 302


def test_new_apps_return_to_the_setup_url_after_installing():
    from ai_pycal.github.permissions import manifest

    found = manifest("app", "https://ai.example.org")
    assert found["request_oauth_on_install"] is False
    assert found["setup_url"] == "https://ai.example.org/setup/installed/"
