"""The configuration file of a repository: its versions and each of its errors."""

import pytest

from ai_pycal import errors
from ai_pycal.config import GitHubRemote, RepositoryConfig
from tests.conftest import DATA

HOME = GitHubRemote("PyCalendar", "home")


def parse(text: str) -> RepositoryConfig:
    return RepositoryConfig.parse(text, HOME)


def test_the_test_configuration_has_two_agreements():
    config = parse((DATA / "agreements.yml").read_text())
    assert str(config.version) == "2.1.0"
    assert not config.newer
    ai, cla = config.agreements
    assert (ai.id, ai.name, ai.tag, ai.path) == (
        "ai-policy",
        "AI Policy (example)",
        "main",
        "agreements/ai-policy.md",
    )
    assert ai.repository == GitHubRemote("PyCalendar", "ai.pycal.org-example")
    assert ai.labels == ("ai-policy-accepted",)
    assert cla.labels == ("cla-signed",)
    assert cla.unsigned_labels == ("cla-missing",)
    assert cla.repository.full_name == "PyCalendar/ai.pycal.org-example"


def test_repository_and_tag_are_optional():
    config = parse(
        "version: 1.0.0\nagreements:\n  a:\n    name: A\n    path: A.md\n    pr: {tags: x}\n"
    )
    assert config.agreements[0].repository == HOME
    assert config.agreements[0].tag == ""


def test_a_newer_minor_version_ignores_unknown_keys():
    config = parse(
        "version: 1.3.0\nfuture: 1\nagreements:\n"
        "  a: {name: A, path: A.md, pr: {tags: x, color: red}, new: 2}\n"
    )
    assert config.newer
    assert config.agreements[0].labels == ("x",)


VALID = "  a: {name: A, path: A.md, pr: {tags: x}}\n"


@pytest.mark.parametrize(
    ("text", "error"),
    [
        ("version: [1.0.0", errors.ConfigFileNotYAML),
        ("- a\n- b\n", errors.ConfigFileNotAMapping),
        ("", errors.ConfigFileNotAMapping),
        ("agreements:\n" + VALID, errors.ConfigVersionMissing),
        ("version: 1.0\nagreements:\n" + VALID, errors.ConfigVersionInvalid),
        ("version: '1.0'\nagreements:\n" + VALID, errors.ConfigVersionInvalid),
        ("version: 3.0.0\nagreements:\n" + VALID, errors.ConfigVersionUnsupported),
        ("version: 0.9.0\nagreements:\n" + VALID, errors.ConfigVersionUnsupported),
        ("version: 1.0.0\nagreement:\n" + VALID, errors.UnknownConfigKey),
        ("version: 1.0.0\n", errors.NoAgreements),
        ("version: 1.0.0\nagreements: [a]\n", errors.NoAgreements),
        (
            "version: 1.0.0\nagreements:\n  A B: {name: A, path: A.md, pr: {tags: x}}\n",
            errors.InvalidAgreementId,
        ),
        ("version: 1.0.0\nagreements:\n  a: text\n", errors.AgreementNotAMapping),
        (
            "version: 1.0.0\nagreements:\n  a: {path: A.md, pr: {tags: x}}\n",
            errors.MissingAgreementField,
        ),
        (
            "version: 1.0.0\nagreements:\n  a: {name: A, pr: {tags: x}}\n",
            errors.MissingAgreementField,
        ),
        ("version: 1.0.0\nagreements:\n  a: {name: A, path: A.md}\n", errors.MissingAgreementField),
        (
            "version: 1.0.0\nagreements:\n  a: {name: A, path: A.md, pr: {tags: []}}\n",
            errors.MissingAgreementField,
        ),
        (
            "version: 1.0.0\nagreements:\n  a: {name: [A], path: A.md, pr: {tags: x}}\n",
            errors.InvalidAgreementField,
        ),
        (
            "version: 1.0.0\nagreements:\n  a: {name: A, path: A.md, pr: x}\n",
            errors.InvalidAgreementField,
        ),
        (
            "version: 1.0.0\nagreements:\n  a: {name: A, path: A.md, pr: {tags: {a: b}}}\n",
            errors.InvalidAgreementField,
        ),
        (
            "version: 1.0.0\nagreements:\n  a: {name: A, path: A.md, pr: {tags: [1]}}\n",
            errors.InvalidAgreementField,
        ),
        (
            "version: 1.0.0\nagreements:\n  a: {name: A, path: /A.md, pr: {tags: x}}\n",
            errors.InvalidAgreementPath,
        ),
        (
            "version: 1.0.0\nagreements:\n  a: {name: A, path: ../A.md, pr: {tags: x}}\n",
            errors.InvalidAgreementPath,
        ),
        (
            "version: 1.0.0\nagreements:\n  a: {name: A, path: docs/, pr: {tags: x}}\n",
            errors.InvalidAgreementPath,
        ),
        (
            "version: 1.0.0\nagreements:\n  a: {name: A, path: A.md, pr: {tags: ' '}}\n",
            errors.InvalidLabel,
        ),
        (
            "version: 1.0.0\nagreements:\n  a: {name: A, path: A.md, pr: {tags: "
            + "x" * 51
            + "}}\n",
            errors.InvalidLabel,
        ),
        (
            "version: 1.0.0\nagreements:\n  a: {name: A, path: A.md, pr: {tags: x, labels: y}}\n",
            errors.UnknownConfigKey,
        ),
        (
            "version: 1.0.0\nagreements:\n  a: {name: A, path: A.md, pr: {tags: x}, tags: y}\n",
            errors.UnknownConfigKey,
        ),
        (
            "version: 1.0.0\nagreements:\n  a: {name: A, path: A.md, pr: {tags: x}, repository: https://gitlab.com/a/b}\n",
            errors.UnsupportedRemote,
        ),
    ],
)
def test_each_mistake_has_its_own_error(text, error):
    with pytest.raises(error) as raised:
        parse(text)
    assert type(raised.value) is error


@pytest.mark.parametrize(
    "remote",
    [
        "https://github.com/PyCalendar/icalendar",
        "https://github.com/PyCalendar/icalendar.git",
        "https://github.com/PyCalendar/icalendar/",
        "git@github.com:PyCalendar/icalendar.git",
        "ssh://git@github.com/PyCalendar/icalendar.git",
        "PyCalendar/icalendar",
    ],
)
def test_remotes_of_github(remote):
    assert GitHubRemote.parse(remote).full_name == "PyCalendar/icalendar"


@pytest.mark.parametrize("remote", ["https://gitlab.com/a/b", "a", "https://github.com/a", "a/.."])
def test_other_remotes_are_refused(remote):
    with pytest.raises(errors.UnsupportedRemote):
        GitHubRemote.parse(remote)


def test_unsigned_labels_are_read_since_2_1_0():
    config = parse(
        "version: 2.1.0\nagreements:\n  a:\n    name: A\n    path: A.md\n"
        "    pr: {labels: signed, unsigned-labels: [missing, also-missing]}\n"
    )
    assert config.agreements[0].labels == ("signed",)
    assert config.agreements[0].unsigned_labels == ("missing", "also-missing")


def test_unknown_keys_of_pr_are_still_refused():
    with pytest.raises(errors.UnknownConfigKey):
        parse(
            "version: 2.1.0\nagreements:\n  a:\n    name: A\n    path: A.md\n"
            "    pr: {labels: x, unsinged-labels: y}\n"
        )
