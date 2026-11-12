"""The rules of AGENTS.md that can be checked."""

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
PACKAGE = ROOT / "ai_pycal"
MODULES = sorted(
    p for p in PACKAGE.rglob("*.py") if "migrations" not in p.parts and "errors" not in p.parts
)


@pytest.mark.parametrize("module", MODULES, ids=lambda p: str(p.relative_to(ROOT)))
def test_one_class_per_module(module):
    tree = ast.parse(module.read_text())
    classes = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
    if module.name == "admin.py":
        return  # one admin per model, registered together
    assert len(classes) <= 1 + (module.name == "pull_request_check.py") + (
        module.name == "agreement_diff.py"
    ), classes


# the scripts that may enhance the pages; each page works without them
SCRIPTS = {"local-time.js"}


def test_no_inline_javascript_in_templates():
    for template in (PACKAGE / "templates").rglob("*.html"):
        text = template.read_text()
        assert "javascript:" not in text and not re.search(r"\son[a-z]+=", text), template
        for tag in re.findall(r"<script[^>]*>.*?</script>", text, re.DOTALL):
            match = re.fullmatch(r'<script src="\{% static \'([\w.-]+)\' %\}" defer></script>', tag)
            assert match and match.group(1) in SCRIPTS, (template, tag)
        assert text.count("<script") == len(re.findall(r"<script[^>]*>.*?</script>", text, re.S))


def test_the_scripts_exist():
    for script in SCRIPTS:
        assert (ROOT / "static" / script).is_file(), script


def test_the_license_is_agpl():
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in (ROOT / "LICENSE").read_text()
    assert 'license = "AGPL-3.0-or-later"' in (ROOT / "pyproject.toml").read_text()
