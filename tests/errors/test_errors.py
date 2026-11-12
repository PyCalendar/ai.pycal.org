"""Every error has its own class, a title, help and a link to the documentation."""

from pathlib import Path

import httpx
import pytest

from ai_pycal import errors

ALL = errors.all_errors()
DOCS = Path(__file__).parents[2] / "docs"


@pytest.mark.parametrize("name", sorted(ALL))
def test_every_error_explains_itself(name):
    cls = ALL[name]
    assert cls.title and (cls.title != "Something went wrong" or cls is errors.AgreementError)
    assert cls.__doc__ and len(cls.__doc__.split()) >= 10, "say what happened and what to do"
    assert cls.docs_url() == (
        f"https://docs.ai.pycal.org/reference/errors.html#{cls.__module__}.{name}"
    )
    assert cls.__module__.startswith("ai_pycal.errors.")
    assert 400 <= cls.status < 600


@pytest.mark.parametrize("name", sorted(ALL))
def test_the_guides_of_the_errors_exist(name):
    guide = ALL[name].guide
    if guide:
        assert (DOCS / guide.replace(".html", ".rst")).is_file(), guide


def test_every_module_of_errors_is_in_the_documentation():
    reference = (DOCS / "reference" / "errors.rst").read_text()
    for module in {cls.__module__ for cls in ALL.values()}:
        assert f"automodule:: {module}" in reference, module


def test_every_error_is_exported():
    for name in ALL:
        assert getattr(errors, name) is ALL[name]


@pytest.mark.parametrize(
    ("raised", "expected"),
    [
        (httpx.ConnectError("down"), errors.GitHubUnreachable),
        (httpx.DecodingError("odd"), errors.GitHubError),
        (KeyError("k"), errors.UnexpectedError),
        (errors.NoAgreements("x"), errors.NoAgreements),
    ],
)
def test_translation_table(raised, expected):
    assert type(errors.translate(raised)) is expected


@pytest.mark.django_db
def test_unreachable_github(client, github, repository):
    from tests.conftest import pull_payload, send_webhook

    payload = pull_payload(github, 1)
    github.unreachable = True
    assert send_webhook(client, "pull_request", payload).json()["error"] == "GitHubUnreachable"


@pytest.mark.django_db
def test_rate_limit(github, repository):
    import httpx as h

    from ai_pycal.github.client import GitHubClient

    github.handle = lambda request: h.Response(
        403, headers={"x-ratelimit-remaining": "0"}, json={"message": "API rate limit exceeded"}
    )
    from ai_pycal.github import client as module

    module.TRANSPORT = h.MockTransport(github.handle)
    with pytest.raises(errors.GitHubRateLimited):
        GitHubClient("t").get("/x")


@pytest.mark.parametrize("url", ["http://localhost:8000/", "https://docs.example/preview"])
def test_every_error_uses_the_configured_docs_root(settings, url):
    settings.DOCS_URL = url
    base = url.rstrip("/") + "/"
    for cls in ALL.values():
        assert cls.docs_url() == f"{base}reference/errors.html#{cls.__module__}.{cls.__name__}"
        assert cls.guide_url() == (base + cls.guide if cls.guide else "")
