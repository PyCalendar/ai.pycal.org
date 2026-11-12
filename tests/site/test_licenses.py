"""The page of the licenses: the project, code from other projects, the Python packages."""

import pytest

pytestmark = pytest.mark.django_db


def test_the_footer_links_the_license_to_the_page(client):
    footer = client.get("/").content.decode().split('<footer class="footer">')[1]
    assert '<a href="/licenses/">AGPL-3.0-or-later</a>' in footer


def test_the_page_lists_the_licenses(client):
    page = client.get("/licenses/").content.decode()
    for name in ("AGPL-3.0-or-later", "CC-BY-SA-4.0", "MIT"):
        assert f'href="/licenses/{name}/"' in page
    reused = page.split('id="reused"')[1].split("</section>")[0]
    assert "<code>ai_pycal/github_mark.py</code>" in reused and "GitHub Inc." in reused
    assert "<code>static/img/favicon.png</code>" in reused
    packages = page.split('id="packages"')[1]
    assert ">Django</a>" in packages and ">reuse</a>" in packages


def test_license_texts(client):
    response = client.get("/licenses/AGPL-3.0-or-later/")
    assert response["Content-Type"] == "text/plain; charset=utf-8"
    assert b"GNU AFFERO GENERAL PUBLIC LICENSE" in response.content
    assert client.get("/licenses/NOPE/").status_code == 404
    assert client.get("/licenses/../settings/").status_code == 404


def test_package_license_texts(client):
    assert b"Django Software Foundation" in client.get("/licenses/packages/django/").content
    assert client.get("/licenses/packages/not-installed/").status_code == 404


def test_the_image_contains_the_license_texts():
    from pathlib import Path

    dockerfile = (Path(__file__).parents[2] / "Dockerfile").read_text()
    assert "COPY LICENSES LICENSES" in dockerfile
