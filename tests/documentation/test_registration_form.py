"""Check the generated documentation form and exercise its browser logic offline."""

import html
import json
import os
import re
import runpy
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_pycal.github.permissions import manifest

ROOT = Path(__file__).parents[2]


@pytest.fixture
def registration_form():
    extension = runpy.run_path(str(ROOT / "docs/_ext/github_app_form.py"))
    directive = extension["GitHubAppForm"].__new__(extension["GitHubAppForm"])
    dependencies = []
    directive.state = SimpleNamespace(
        document=SimpleNamespace(
            settings=SimpleNamespace(env=SimpleNamespace(note_dependency=dependencies.append))
        )
    )
    result = directive.run()
    assert str(ROOT / "ai_pycal/github/permissions.py") in dependencies
    return result[0].astext()


def test_documentation_form_posts_only_manifest_to_github(registration_form):
    assert 'action="https://github.com/settings/apps/new"' in registration_form
    assert 'method="post"' in registration_form
    assert 'target="_blank" rel="noopener"' in registration_form
    assert re.findall(r'<input[^>]*\bname="([^"]+)"', registration_form) == ["manifest"]
    hidden = re.search(r'id="app-manifest"[^>]*value="([^"]+)"', registration_form).group(1)
    assert json.loads(html.unescape(hidden)) == manifest("", "http://localhost:5000")
    assert "__MANIFEST__" not in registration_form
    assert "<script" not in registration_form


@pytest.mark.skipif(not shutil.which("node"), reason="Node is needed to exercise docs JavaScript")
def test_registration_form_browser_logic(registration_form):
    result = subprocess.run(
        [shutil.which("node"), "--test", str(ROOT / "tests/documentation/registration_form.cjs")],
        env={**os.environ, "GITHUB_FORM_HTML": registration_form},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
