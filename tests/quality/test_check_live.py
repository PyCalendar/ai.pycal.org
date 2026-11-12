"""make check-live: the walk through a live site, here against the site of the tests."""

import httpx
import pytest

from scripts.check_live import LiveCheck
from tests.conftest import REPOSITORY

pytestmark = pytest.mark.django_db


def django_transport(client):
    """Answer the requests of the check with the Django test client."""

    def handle(request: httpx.Request) -> httpx.Response:
        path = request.url.raw_path.decode()
        if request.method == "POST":
            answer = client.generic(
                "POST",
                path,
                request.content,
                content_type="application/json",
                HTTP_X_GITHUB_EVENT=request.headers.get("x-github-event", ""),
            )
        else:
            answer = client.get(path)
        headers = {key: value for key, value in answer.items()}
        body = b"".join(answer.streaming_content) if answer.streaming else answer.content
        return httpx.Response(answer.status_code, headers=headers, content=body)

    return httpx.MockTransport(handle)


def check(client) -> LiveCheck:
    transport = httpx.Client(transport=django_transport(client), base_url="http://testserver")
    return LiveCheck("http://testserver", client=transport, wait=0)


def test_the_site_of_the_tests_passes(client, github, repository, alice, capsys, settings):
    from tests.conftest import pull_payload, send_webhook, sign_agreement
    from tests.pulls.test_labels import versions

    settings.FAVICON = ""
    send_webhook(client, "pull_request", pull_payload(github, 1))
    client.force_login(alice)
    sign_agreement(client, versions(repository)["cla"], "alice")
    client.logout()
    live = check(client)
    assert live.run() == 0, live.failures
    out = capsys.readouterr().out
    assert f"project /project/{REPOSITORY}/" in out
    for page in (
        f"/project/{REPOSITORY}/",
        f"/project/{REPOSITORY}/pulls/1/",
        f"/logs/{REPOSITORY}/pulls/1/",
        "/contributor/alice/",
        "/logs/contributor/alice/",
    ):
        assert live.checked.get(page) == 200, page
    assert any(path.startswith("/agreements/history/") for path in live.checked)


def test_a_public_page_that_asks_to_sign_in_fails():
    def handle(request):
        return httpx.Response(302, headers={"location": "/accounts/login/?next=/about/"})

    live = LiveCheck("http://site", client=httpx.Client(transport=httpx.MockTransport(handle)))
    live.check_page("/about/")
    assert "public, but asks to sign in" in live.failures[0]


def test_a_redirect_away_from_the_site_fails():
    def handle(request):
        return httpx.Response(302, headers={"location": "https://elsewhere.example/"})

    live = LiveCheck("http://site", client=httpx.Client(transport=httpx.MockTransport(handle)))
    live.check_page("/about/")
    assert "leaves to https://elsewhere.example/" in live.failures[0]
    live.check_page("/favicon.ico")  # the icon may be elsewhere
    assert len(live.failures) == 1


def test_without_a_public_project_it_fails(client, repository):
    repository.private = True
    repository.save()
    live = check(client)
    assert live.run() == 1
    assert any("no public project" in line for line in live.failures)


def test_it_waits_while_the_site_starts(monkeypatch):
    answers = iter([502, 503, 200])
    transport = httpx.MockTransport(lambda request: httpx.Response(next(answers)))
    live = LiveCheck("http://site", client=httpx.Client(transport=transport), wait=60)
    monkeypatch.setattr("scripts.check_live.time.sleep", lambda seconds: None)
    assert live.wait_until_up()


def test_it_gives_up_after_the_time(monkeypatch):
    transport = httpx.MockTransport(lambda request: httpx.Response(503))
    live = LiveCheck("http://site", client=httpx.Client(transport=transport), wait=0)
    assert not live.wait_until_up()
    assert "did not start" in live.failures[0]


def test_a_500_instead_of_a_404_fails():
    transport = httpx.MockTransport(lambda request: httpx.Response(500, text="Server Error"))
    live = LiveCheck("http://site", client=httpx.Client(transport=transport))
    live.expect("/missing/", (404,))
    assert live.failures and "expected 404" in live.failures[0]


def test_a_404_without_the_page_of_the_site_fails():
    transport = httpx.MockTransport(lambda request: httpx.Response(404, text="Not Found"))
    live = LiveCheck("http://site", client=httpx.Client(transport=transport))
    live.expect("/missing/", (404,))
    assert "error page of the site" in live.failures[0]


def test_the_sign_in_page_does_not_nest_its_address(client):
    page = client.get("/accounts/login/?next=/projects/").content.decode()
    assert "next=/accounts/login/" not in page and "next=%2Faccounts" not in page
