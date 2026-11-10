"""Test agreements match example/, with both policies mandatory in the test fixture."""

import pytest
import yaml

from ai_pycal.config import GitHubRemote, RepositoryConfig
from tests.conftest import DATA, EXAMPLE

pytestmark = pytest.mark.skipif(
    not (EXAMPLE / ".github" / "agreements.yml").exists(), reason="no example checkout"
)


def test_the_example_configuration_is_valid():
    text = (EXAMPLE / ".github" / "agreements.yml").read_text()
    config = RepositoryConfig.parse(text, GitHubRemote("PyCalendar", "ai.pycal.org-example"))
    for spec in config.agreements:
        assert (EXAMPLE / spec.path).is_file(), spec.path


def test_the_fixture_uses_the_mandatory_variant_of_the_example():
    example = yaml.safe_load((EXAMPLE / ".github" / "agreements.yml").read_text())
    fixture = yaml.safe_load((DATA / "agreements.yml").read_text())
    assert example["agreements"]["ai-policy"]["mandatory"] is False
    assert fixture["agreements"]["ai-policy"]["mandatory"] is True
    example["agreements"]["ai-policy"]["mandatory"] = True
    assert example == fixture


@pytest.mark.parametrize(
    ("example", "data"),
    [
        ("agreements/ai-policy.md", "ai-policy.md"),
        ("agreements/cla.md", "cla.md"),
    ],
)
def test_the_tests_use_the_example(example, data):
    assert (EXAMPLE / example).read_text() == (DATA / data).read_text()
