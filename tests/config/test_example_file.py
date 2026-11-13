"""The example configuration file to copy: the newest format, every field explained."""

from pathlib import Path

import pytest

from ai_pycal import errors
from ai_pycal.config.agreement_spec import KEYS as AGREEMENT_KEYS
from ai_pycal.config.format_version import SUPPORTED
from ai_pycal.config.remote import GitHubRemote
from ai_pycal.config.repository_config import EXAMPLE, RepositoryConfig

ROOT = Path(__file__).parents[2]
FILE = ROOT / "docs" / EXAMPLE


def test_the_example_uses_the_newest_format():
    config = RepositoryConfig.parse(FILE.read_text(), GitHubRemote("o", "r"))
    assert config.version == SUPPORTED
    assert not config.newer
    assert config.choices


def test_the_version_is_the_first_line_that_is_no_comment():
    lines = [line for line in FILE.read_text().splitlines() if line and line[0] != "#"]
    assert lines[0] == f"version: {SUPPORTED}"


def test_every_field_of_an_agreement_is_in_the_example():
    text = FILE.read_text()
    for key in AGREEMENT_KEYS | {"labels", "unsigned-labels", "choices", "default"}:
        assert f" {key}:" in text or f"\n{key}:" in text, key


def test_the_errors_of_the_version_name_the_newest_one():
    assert f"version: {SUPPORTED}" in errors.ConfigVersionMissing.__doc__
    assert str(SUPPORTED) in errors.ConfigVersionInvalid.__doc__
    assert "1.0.0" not in errors.ConfigVersionMissing.__doc__ + errors.ConfigVersionInvalid.__doc__


def test_a_missing_version_says_what_to_add(settings):
    settings.DOCS_URL = "https://docs.example.org/"
    with pytest.raises(errors.ConfigVersionMissing) as raised:
        RepositoryConfig.parse("agreements: {}\n", GitHubRemote("o", "r"))
    assert f"add version: {SUPPORTED} as the first line" in str(raised.value)
    assert "https://docs.example.org/_static/agreements.yml" in str(raised.value)


def test_the_documentation_shows_the_example():
    page = (ROOT / "docs" / "reference" / "config-file.rst").read_text()
    assert ".. literalinclude:: ../_static/agreements.yml" in page
