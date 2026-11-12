"""The About page: the links of the footer, the version, its commit, its time and its build."""

import json

import pytest

from ai_pycal import build_info
from ai_pycal.errors import InvalidFooterLink
from ai_pycal.footer_links import parse_footer_links

pytestmark = pytest.mark.django_db

BUILD = {
    "version": "1.2.3",
    "built": "2026-11-12T14:00:00+00:00",
    "commit": "4cbfd3e",
    "commit_full": "4cbfd3edf2dcf1976b57ecf2c71ab35a9e0ccbdc",
    "message": "Add the <b>about</b> page",
    "committed": "2026-11-12T13:30:00+00:00",
    "tag": "v1.2.3",
    "build_url": "https://github.com/PyCalendar/sign.pycal.org/actions/runs/43245171349",
}


@pytest.fixture
def built(tmp_path, monkeypatch):
    """A version.json as the image has it."""
    path = tmp_path / "version.json"
    path.write_text(json.dumps(BUILD))
    monkeypatch.setattr(build_info, "VERSION_FILE", path)
    build_info.get.cache_clear()
    yield
    build_info.get.cache_clear()


def test_the_about_page_shows_the_build(client, built):
    page = client.get("/about/").content.decode()
    source = "https://github.com/PyCalendar/sign.pycal.org"
    assert '<code>4cbfd3e</code> <a class="github-link github-link-icon"' in page
    assert (
        f'href="{source}/commit/{BUILD["commit_full"]}" aria-label="This commit on GitHub"' in page
    )
    assert "Add the &lt;b&gt;about&lt;/b&gt; page" in page
    assert f'<a href="{source}/tree/v1.2.3">1.2.3</a>' in page
    # how long ago, the exact time in UTC on hover; the browser shows its local time
    assert 'datetime="2026-11-12T13:30:00Z" title="2026-11-12 13:30 UTC">' in page
    assert 'datetime="2026-11-12T14:00:00Z" title="2026-11-12 14:00 UTC">' in page
    assert f'href="{BUILD["build_url"]}" title="GitHub Actions run">' in page


def test_a_checkout_shows_the_commit_of_git(client, tmp_path, monkeypatch):
    monkeypatch.setattr(build_info, "VERSION_FILE", tmp_path / "missing.json")
    build_info.get.cache_clear()
    try:
        page = client.get("/about/").content.decode()
        info = build_info.get("https://example.org/code")
    finally:
        build_info.get.cache_clear()
    assert info["version"] == "development"
    assert "Not built by the CI" in page
    if info["commit"]:  # a checkout with git
        assert info["code_url"] == f"https://example.org/code/tree/{info['commit_full']}"
        assert info["committed_at"] is not None
        assert info["commit"] in page


def test_without_git_the_page_still_works(client, tmp_path, monkeypatch):
    monkeypatch.setattr(build_info, "VERSION_FILE", tmp_path / "missing.json")
    monkeypatch.setattr(build_info.subprocess, "run", _no_git)
    build_info.get.cache_clear()
    try:
        response = client.get("/about/")
        assert build_info.get("https://example.org")["code_url"] == "https://example.org"
    finally:
        build_info.get.cache_clear()
    assert response.status_code == 200
    assert "development" in response.content.decode()


def _no_git(*args, **kwargs):
    raise FileNotFoundError("git")


def test_the_footer_has_about_and_the_footer_links(client):
    page = client.get("/").content.decode()
    footer = page.split('<footer class="footer">')[1].split("</footer>")[0]
    assert 'href="/about/"' in footer
    assert '<a href="https://pycal.org">pycal.org</a>' in footer
    about = client.get("/about/").content.decode()
    main = about.split("<main")[1].split("</main>")[0]
    assert "https://pycal.org" not in main  # only in the footer


def test_the_footer_links_can_be_changed(client, settings):
    settings.FOOTER_LINKS = [("Example", "https://example.org/"), ("Blog", "https://b.example/")]
    for url in ("/", "/about/"):
        page = client.get(url).content.decode()
        assert '<a href="https://example.org/">Example</a>' in page
        assert '<a href="https://b.example/">Blog</a>' in page
        assert "https://pycal.org" not in page


@pytest.mark.parametrize("value", ["pycal.org", "=https://pycal.org", "x=javascript:alert(1)"])
def test_wrong_footer_links(value):
    with pytest.raises(InvalidFooterLink):
        parse_footer_links(value)
