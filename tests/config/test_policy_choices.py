"""Version 2 policies and choice validation, alongside the version 1 reader."""

import pytest
import yaml

from ai_pycal import errors
from ai_pycal.config import GitHubRemote, RepositoryConfig

HOME = GitHubRemote("collective", "icalendar")


def configuration():
    return {
        "version": "2.0.0",
        "agreements": {
            "cla": {"name": "CLA", "path": "cla.md", "mandatory": True},
            "ai": {
                "name": "AI policy",
                "path": "ai.md",
                "ref": "v1",
                "mandatory": False,
                "description": "**AI use** explained",
                "pr": {"labels": ["ai-signed"]},
            },
        },
        "choices": [
            {
                "name": "AI allowed",
                "description": "Use AI under this policy.",
                "agreements": ["ai"],
                "default": True,
                "pr": {"labels": ["ai"]},
            }
        ],
    }


def test_v2_reads_ref_labels_descriptions_and_choices():
    config = RepositoryConfig.parse(yaml.safe_dump(configuration()), HOME)
    agreements = {a.id: a for a in config.agreements}
    assert agreements["cla"].mandatory
    assert not agreements["ai"].mandatory
    assert agreements["ai"].ref == "v1"
    assert agreements["ai"].labels == ("ai-signed",)
    assert config.choices[0].key == "ai-allowed"
    assert config.choices[0].default
    assert config.choices[0].agreements == ("ai",)


@pytest.mark.parametrize(
    ("where", "field", "value", "error"),
    [
        ("agreement", "mandatory", "true", errors.InvalidMandatory),
        ("agreement", "description", [], errors.InvalidAgreementField),
        ("agreement", "tag", "main", errors.UnknownConfigKey),
        ("agreement", "pr", {"tags": ["old"]}, errors.UnknownConfigKey),
        ("choice", "name", "", errors.InvalidChoiceField),
        ("choice", "name", "!!!", errors.InvalidChoiceField),
        ("choice", "description", False, errors.InvalidChoiceField),
        ("choice", "agreements", "ai", errors.InvalidChoiceField),
        ("choice", "agreements", [], errors.InvalidChoiceField),
        ("choice", "agreements", ["missing"], errors.UnknownChoiceAgreement),
        ("choice", "agreements", [[]], errors.UnknownChoiceAgreement),
        ("choice", "default", "false", errors.InvalidChoiceField),
        ("choice", "typo", True, errors.UnknownConfigKey),
        ("choice", "pr", {"labels": [""]}, errors.InvalidLabel),
    ],
)
def test_choice_configuration_errors(where, field, value, error):
    data = configuration()
    item = data["agreements"]["ai"] if where == "agreement" else data["choices"][0]
    item[field] = value
    with pytest.raises(error):
        RepositoryConfig.parse(yaml.safe_dump(data), HOME)


@pytest.mark.parametrize("choices", [{}, "wrong", [False]])
def test_choices_are_a_list_of_mappings(choices):
    data = configuration()
    data["choices"] = choices
    with pytest.raises((errors.InvalidChoices, errors.InvalidChoiceField)):
        RepositoryConfig.parse(yaml.safe_dump(data), HOME)


@pytest.mark.parametrize("duplicate", [True, False])
def test_choice_names_and_project_default_are_unique(duplicate):
    data = configuration()
    extra = dict(data["choices"][0])
    if not duplicate:
        extra["name"] = "Another policy"
    data["choices"].append(extra)
    with pytest.raises(errors.DuplicateChoice if duplicate else errors.MultipleDefaultChoices):
        RepositoryConfig.parse(yaml.safe_dump(data), HOME)


def test_no_project_default_is_allowed():
    data = configuration()
    data["choices"][0]["default"] = False
    assert not RepositoryConfig.parse(yaml.safe_dump(data), HOME).choices[0].default
