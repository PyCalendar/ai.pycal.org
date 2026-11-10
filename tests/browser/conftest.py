"""Browser fixtures serve built documentation from memory and block external requests."""

import mimetypes
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest
from playwright.sync_api import sync_playwright

DOCS = Path(__file__).parents[2] / "docs/_build/html"
DOCS_URL = "https://docs.ai-pycal.test"


@pytest.fixture(scope="session")
def chromium():
    assert (DOCS / "index.html").is_file(), "Build the documentation with make docs first."
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture
def browser_context(chromium, request):
    context = chromium.new_context(
        java_script_enabled=getattr(request, "param", True), service_workers="block"
    )
    context.set_default_timeout(5000)

    def route_documentation(route):
        address = urlsplit(route.request.url)
        if address.scheme == "https" and address.netloc == "docs.ai-pycal.test":
            path = (DOCS / unquote(address.path).lstrip("/")).resolve()
            if path.is_relative_to(DOCS.resolve()) and path.is_file():
                content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
                route.fulfill(path=path, content_type=content_type)
                return
        route.abort()

    context.route("**/*", route_documentation)
    yield context
    context.close()


@pytest.fixture
def docs_page(browser_context):
    page = browser_context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    yield page
    assert not errors, errors
