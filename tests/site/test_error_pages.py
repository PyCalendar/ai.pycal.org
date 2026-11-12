"""The pages of errors follow the design of the site and lead back."""

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import Client, RequestFactory

from ai_pycal.views import errors

pytestmark = pytest.mark.django_db


def designed(page: str) -> None:
    """Assert that a page has the design of the site."""
    assert 'href="/static/style.css"' in page
    assert "--brand: #3b79aa;" in page
    assert 'class="status-page' in page
    assert 'class="nav"' in page
    assert "<script" not in page


def test_page_not_found(client):
    response = client.get("/no/such/page/here/")
    assert response.status_code == 404
    page = response.content.decode()
    designed(page)
    assert "<title>Page not found · " in page
    assert '<p class="status-code" aria-hidden="true">404</p>' in page
    assert "Back to the start" in page
    assert "/issues/new" in page
    assert 'class="footer"' in page


@pytest.mark.parametrize(
    ("view", "status", "title"),
    [
        (errors.bad_request, 400, "Bad request"),
        (errors.permission_denied, 403, "Access denied"),
        (errors.page_not_found, 404, "Page not found"),
        (errors.server_error, 500, "Something went wrong"),
    ],
)
def test_every_status_has_a_designed_page(rf, view, status, title):
    request = rf.get("/somewhere/")
    request.user = AnonymousUser()
    response = view(request) if view is errors.server_error else view(request, Exception())
    assert response.status_code == status
    page = response.content.decode()
    designed(page)
    assert f'<h1 id="status-title">{title}</h1>' in page


def test_the_handlers_are_registered():
    from ai_pycal import urls

    assert urls.handler400 == "ai_pycal.views.errors.bad_request"
    assert urls.handler403 == "ai_pycal.views.errors.permission_denied"
    assert urls.handler404 == "ai_pycal.views.errors.page_not_found"
    assert urls.handler500 == "ai_pycal.views.errors.server_error"


def test_an_expired_form_explains_what_to_do():
    client = Client(enforce_csrf_checks=True)
    response = client.post("/theme/", {"theme": "dark"})
    assert response.status_code == 403
    page = response.content.decode()
    designed(page)
    assert "The form has expired" in page
    assert "reload the page and send the form again" in page


def test_the_server_error_page_works_without_the_database(monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("the database is down")

    monkeypatch.setattr(errors, "render", broken)
    response = errors.server_error(RequestFactory().get("/"))
    assert response.status_code == 500
    page = response.content.decode()
    designed(page)
    assert "Something went wrong" in page
    assert "/issues/new" in page
    assert 'class="footer"' not in page


def test_the_server_error_page_falls_back_to_text(monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("broken")

    monkeypatch.setattr(errors, "render", broken)
    monkeypatch.setattr(errors, "render_to_string", broken)
    response = errors.server_error(RequestFactory().get("/"))
    assert response.status_code == 500
    assert response["Content-Type"] == "text/plain; charset=utf-8"
    assert response.content.decode().startswith("Something went wrong")


def test_a_raised_exception_shows_the_designed_page(settings):
    settings.ROOT_URLCONF = "tests.site.failing_urls"
    response = Client(raise_request_exception=False).get("/fail/")
    assert response.status_code == 500
    designed(response.content.decode())


def test_errors_of_the_site_share_the_design(client):
    page = client.get("/project/nobody/nothing/pulls/1/").content.decode()
    designed(page)
    assert "data-error=" in page
    assert "What this error means and how to solve it" in page
