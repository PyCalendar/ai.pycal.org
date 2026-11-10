"""Exercise real browser navigation, native validation and intercepted manifest POSTs."""

import json
import re
from urllib.parse import parse_qs, urlsplit

import pytest
from playwright.sync_api import expect

from ai_pycal.github.permissions import manifest
from tests.browser.conftest import DOCS_URL

FORM_URL = f"{DOCS_URL}/how-to/create-github-app.html"


@pytest.mark.parametrize(
    "filename,title",
    [
        ("create-github-app", "App manifest with the submission form"),
        ("github-app-manifest", "App manifest CLI flow"),
        ("github-app-manual", "Manual app creation"),
    ],
)
def test_common_page_links_to_each_complete_flow(docs_page, filename, title):
    docs_page.goto(f"{DOCS_URL}/how-to/github-app.html")
    article = docs_page.locator("article")
    expect(article.locator("table tbody tr").first).to_contain_text("recommended default")
    article.get_by_role("link", name=title, exact=True).click()
    expect(docs_page).to_have_url(f"{DOCS_URL}/how-to/{filename}.html")
    expect(docs_page.locator("article").get_by_role("heading", level=1)).to_contain_text(title)
    expect(docs_page.locator("article")).to_contain_text("GITHUB_WEBHOOK_SECRET")
    expect(docs_page.locator("article")).to_contain_text("Install the GitHub App")
    if filename == "create-github-app":
        expect(docs_page.get_by_role("button", name="Create app on GitHub")).to_be_enabled()


@pytest.mark.parametrize(
    "owner,site_url,webhook_url",
    [
        ("", "http://localhost:5000", ""),
        ("PyCalendar-test", "https://ai.example.org/service/", "https://forward.example/webhook/"),
    ],
)
def test_native_manifest_post_and_downloaded_state(
    docs_page, browser_context, tmp_path, owner, site_url, webhook_url
):
    submissions = []

    def capture_registration(route):
        submissions.append(route.request)
        route.fulfill(content_type="text/html", body="<p>Registration intercepted locally.</p>")

    browser_context.route("https://github.com/**", capture_registration)
    docs_page.goto(FORM_URL)
    name = 'Test app "quotes" <&>'
    docs_page.get_by_label(re.compile("^GitHub App name")).fill(name)
    docs_page.get_by_label(re.compile("^Site URL")).fill(site_url)
    docs_page.get_by_label(re.compile("^GitHub organization")).fill(owner)
    docs_page.get_by_label(re.compile("^Forwarded webhook URL")).fill(webhook_url)
    with docs_page.expect_popup() as opened:
        docs_page.get_by_role("button", name="Create app on GitHub").click()
    opened.value.wait_for_load_state("domcontentloaded")
    assert len(submissions) == 1
    request = submissions[0]
    assert request.method == "POST"
    destination = urlsplit(request.url)
    assert destination.netloc == "github.com"
    assert destination.path == (
        f"/organizations/{owner}/settings/apps/new" if owner else "/settings/apps/new"
    )
    fields = parse_qs(request.post_data)
    assert set(fields) == {"manifest"}
    expected = manifest(name, site_url.rstrip("/"))
    if webhook_url:
        expected["hook_attributes"]["url"] = webhook_url
    assert json.loads(fields["manifest"][0]) == expected
    state = parse_qs(destination.query)["state"][0]
    assert re.fullmatch(r"[0-9a-f]{64}", state)
    expect(docs_page).to_have_url(FORM_URL)
    with docs_page.expect_download() as download:
        docs_page.get_by_role("link", name="Save registration state").click()
    assert download.value.suggested_filename == "github-app-state.txt"
    saved = tmp_path / download.value.suggested_filename
    download.value.save_as(saved)
    assert saved.read_text() == state
    preview = docs_page.locator("#app-manifest-preview").text_content()
    assert json.loads(preview) == expected


@pytest.mark.parametrize(
    "field,value,validity",
    [("app-name", "", "valueMissing"), ("app-organization", "bad/owner", "patternMismatch")],
)
def test_native_validation_prevents_registration(
    docs_page, browser_context, field, value, validity
):
    docs_page.goto(FORM_URL)
    docs_page.locator("#app-name").fill("Test app")
    docs_page.locator(f"#{field}").fill(value)
    docs_page.get_by_role("button", name="Create app on GitHub").click()
    assert docs_page.locator(f"#{field}").evaluate(f"element => element.validity.{validity}")
    expect(docs_page.locator("#app-save-state")).to_be_hidden()
    assert len(browser_context.pages) == 1


@pytest.mark.parametrize(
    "field,value,message",
    [
        ("app-site-url", "javascript:alert(1)", "Use an HTTP or HTTPS URL"),
        ("app-site-url", "https://example.org/?query=1", "must not contain a query string"),
        ("app-webhook-url", "https://name:secret@example.org/hook/", "without login details"),
    ],
)
def test_invalid_address_shows_error_and_recovers(docs_page, field, value, message):
    docs_page.goto(FORM_URL)
    docs_page.locator("#app-name").fill("Test app")
    docs_page.locator(f"#{field}").fill(value)
    expect(docs_page.locator("#app-form-error")).to_contain_text(message)
    expect(docs_page.get_by_role("button", name="Create app on GitHub")).to_be_disabled()
    expect(docs_page.locator("#app-manifest")).to_have_value("")
    docs_page.locator(f"#{field}").fill("https://example.org/")
    expect(docs_page.locator("#app-form-error")).to_be_hidden()
    expect(docs_page.get_by_role("button", name="Create app on GitHub")).to_be_enabled()


@pytest.mark.parametrize("browser_context", [False], indirect=True)
def test_form_without_javascript_explains_the_cli_alternative(docs_page):
    docs_page.goto(FORM_URL)
    expect(docs_page.get_by_role("button", name="Create app on GitHub")).to_be_disabled()
    fallback = docs_page.locator("#github-app-form").get_by_role(
        "link", name="App manifest CLI flow"
    )
    expect(fallback).to_be_visible()
    fallback.click()
    expect(docs_page.locator("article").get_by_role("heading", level=1)).to_contain_text(
        "App manifest CLI flow"
    )
