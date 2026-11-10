"""The rules of AGENTS.md that can be checked."""

import ast
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


def test_no_javascript_in_templates():
    for template in (PACKAGE / "templates").rglob("*.html"):
        text = template.read_text()
        assert "<script" not in text and "javascript:" not in text and " onclick=" not in text, (
            template
        )


def test_the_license_is_agpl():
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in (ROOT / "LICENSE").read_text()
    assert 'license = "AGPL-3.0-or-later"' in (ROOT / "pyproject.toml").read_text()
