"""Links to GitHub show the mark of GitHub; alone, with a label, where it is clear."""

from pathlib import Path

import pytest
from django.template import Context, Template

from ai_pycal.github_mark import PATH

ROOT = Path(__file__).parents[2]
pytestmark = pytest.mark.django_db


def render(text: str, **context) -> str:
    return Template("{% load github %}" + text).render(Context(context))


def test_the_mark_alone_has_a_label():
    html = render(
        '{% github_link url "PyCalendar/icalendar on GitHub" %}', url="https://github.com/x"
    )
    assert 'aria-label="PyCalendar/icalendar on GitHub"' in html
    assert 'title="PyCalendar/icalendar on GitHub"' in html
    assert 'href="https://github.com/x"' in html
    assert PATH in html
    assert 'aria-hidden="true"' in html
    assert "<span>" not in html


def test_the_mark_before_a_text():
    html = render(
        '{% github_link url "Source" "Source code" "button" %}', url="https://github.com/x"
    )
    assert 'class="github-link button"' in html
    assert "<span>Source code</span>" in html
    assert "aria-label" not in html


def test_no_address_no_link():
    assert render('{% github_link url "x" %}', url="") == ""


def test_the_footer_and_the_repository_title(client, repository):
    page = client.get(f"/project/{repository.full_name}/").content.decode()
    title = page.split('<div class="crumbs">')[1].split("</div>")[0]
    assert '<a href="/projects/PyCalendar/">PyCalendar</a>' in title
    assert '</h1> <a class="github-link github-link-icon"' in title
    assert f'aria-label="{repository.full_name} on GitHub"' in title
    about = client.get("/about/").content.decode().split("<main")[1].split("</main>")[0]
    assert about.count('class="icon github-mark"') >= 2  # source code, report a bug


def test_no_template_links_to_github_without_the_mark():
    for template in (ROOT / "ai_pycal" / "templates").rglob("*.html"):
        text = template.read_text()
        if template.name == "licenses.html":
            continue  # the home pages of packages, mostly not on GitHub
        for marker in (
            'href="https://github.com',
            'href="{{ links.source',
            'href="{{ links.issues',
            '.url }}"',
            'html_url }}"',
            'install_url }}"',
            'commit_url }}"',
            'build_url }}"',
        ):
            assert marker not in text, (template, marker)


def test_the_license_of_the_mark_is_recorded():
    assert 'path = "ai_pycal/github_mark.py"' in (ROOT / "REUSE.toml").read_text()
    assert (ROOT / "LICENSES" / "MIT.txt").is_file()
