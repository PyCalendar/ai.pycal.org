"""Errors of the configuration file of a repository: ``.github/agreements.yml``.

Each of them is shown to the administrator who adds the repository, and in the
list of repositories until the file is fixed. The format of the file is described
in :doc:`/reference/config-file`.
"""

from django.utils.translation import gettext_lazy as _

from .base import AgreementError


class ConfigFileError(AgreementError):
    """The configuration file of the repository can not be used.

    Fix the file in the default branch of the repository as described in
    :doc:`/reference/config-file` and refresh the repository on the page Setup.
    """

    title = _("The configuration file can not be used")
    guide = "reference/config-file.html"
    guide_title = _("The configuration file")


class ConfigFileNotFound(ConfigFileError):
    """The repository has no configuration file.

    A repository can only be added when its default branch contains the file
    ``.github/agreements.yml``. Add the file, as in the example of
    :doc:`/reference/config-file`, and add the repository again.
    """

    title = _("The repository has no configuration file")
    status = 404


class ConfigFileNotYAML(ConfigFileError):
    """The configuration file is not valid YAML.

    The detail names the line where the YAML can not be read. Check the indentation
    and the quotes there, for example with ``python -c "import yaml, sys;
    yaml.safe_load(open(sys.argv[1]))" .github/agreements.yml``.
    """

    title = _("The configuration file is not valid YAML")


class ConfigFileNotAMapping(ConfigFileError):
    """The configuration file does not contain a mapping of keys and values.

    The file starts with ``version:`` and ``agreements:``, each at the start of a
    line. A list or a single value is not a configuration.
    """

    title = _("The configuration file is not a mapping")


class ConfigVersionMissing(ConfigFileError):
    """The configuration file has no version.

    The version says which format the file uses, so that later formats can be
    read without misunderstanding older files. Add the newest version,
    ``version: 2.2.0``, as the first line, as in the :ref:`example file
    <example-config>`, and check the fields with its comments.
    """

    title = _("The configuration file has no version")


class ConfigVersionInvalid(ConfigFileError):
    """The version of the configuration file is not a version number.

    The version has three numbers separated by dots, such as ``2.2.0``, the
    newest one, as in the :ref:`example file <example-config>`. ``version: 2.2``
    has only two.
    """

    title = _("The version of the configuration file is invalid")


class ConfigVersionUnsupported(ConfigFileError):
    """This site does not know the major version of the configuration file.

    The site reads the versions listed in :doc:`/reference/config-file`. A file of
    a newer major version can only be read by a newer version of the site: use
    the newest version the site supports, or ask the people who run the site to
    update it.
    """

    title = _("The version of the configuration file is not supported")


class UnknownConfigKey(ConfigFileError):
    """The configuration file contains a key this version of the format does not have.

    This is mostly a typing error, such as ``agreement:`` instead of
    ``agreements:``. The detail names the key and where it is. Keys of newer minor
    versions are ignored: raise ``version`` only together with the keys.
    """

    title = _("The configuration file contains an unknown key")


class NoAgreements(ConfigFileError):
    """The configuration file lists no agreements.

    Add at least one agreement under ``agreements:``, with an identifier as key
    and the fields ``name``, ``repository``, ``path`` and ``pr``.
    """

    title = _("The configuration file lists no agreements")


class InvalidAgreementId(ConfigFileError):
    """The identifier of an agreement is not allowed.

    Identifiers are the keys under ``agreements:``. They contain lowercase
    letters, digits, ``-`` and ``_``, start with a letter or a digit and are at
    most 50 characters long, such as ``ai-policy`` or ``cla``.
    """

    title = _("The identifier of an agreement is invalid")


class AgreementNotAMapping(ConfigFileError):
    """An agreement of the configuration file is not a mapping.

    Each agreement is a mapping of the fields ``name``, ``ref``, ``repository``,
    ``path`` and ``pr``, indented below its identifier.
    """

    title = _("An agreement is not a mapping")


class MissingAgreementField(ConfigFileError):
    """An agreement lacks a field it needs.

    The detail names the agreement and the field. ``name`` and ``path`` are
    required; ``ref`` defaults to the default branch and ``repository`` to the
    repository of the configuration file. Version 1 also requires ``pr.tags``.
    """

    title = _("An agreement lacks a field")


class InvalidAgreementField(ConfigFileError):
    """A field of an agreement has a value of the wrong kind.

    The detail names the agreement, the field and what is expected, for example
    text instead of a list. Text can be put in quotes.
    """

    title = _("A field of an agreement is invalid")


class InvalidAgreementPath(ConfigFileError):
    """The path of an agreement is not a path of a file in a repository.

    The path is relative to the root of the repository, such as
    ``agreements/ai-policy.md``. It does not start with ``/`` and contains no
    ``..``.
    """

    title = _("The path of an agreement is invalid")


class InvalidLabel(ConfigFileError):
    """A label of ``pr.labels`` can not be a label of GitHub.

    Labels of GitHub are at most 50 characters long and not empty. ``pr.labels`` is
    one label or a list of labels, such as ``ai-policy-accepted``.
    """

    title = _("A label of the pull requests is invalid")


class InvalidSignMinSeconds(ConfigFileError):
    """The reading time ``sign-min-seconds`` of an agreement is not a number of seconds.

    ``sign-min-seconds`` is the time between opening an agreement and signing it,
    at least: a number from 0 to 3600, such as ``30``. Without it, the site uses
    its own setting ``SIGN_MIN_SECONDS``.
    """

    title = _("The reading time of an agreement is invalid")


class UnsupportedRemote(ConfigFileError):
    """The repository of an agreement is not on GitHub.

    The agreements are read from GitHub. Use the address of a repository on
    GitHub, such as ``https://github.com/PyCalendar/sign.pycal.org-example.git`` or
    ``git@github.com:PyCalendar/sign.pycal.org-example.git``.
    """

    title = _("The repository of an agreement is not on GitHub")


class AgreementRefNotFound(ConfigFileError):
    """The reference of an agreement does not exist in its repository.

    ``ref`` names a tag, a branch or a commit of the repository of the agreement.
    Check the spelling and that it was pushed: ``git push origin <tag>``. A
    private repository of the agreement needs the GitHub App installed on it.
    """

    title = _("The reference of an agreement does not exist")
    status = 404


class AgreementFileNotFound(ConfigFileError):
    """The file of an agreement does not exist at its reference.

    The file ``path`` is read from the repository of the agreement at the commit
    of ``ref``. Check the path and that the file is part of that commit.
    """

    title = _("The file of an agreement does not exist")
    status = 404


class AgreementFileTooLarge(ConfigFileError):
    """The file of an agreement is too large.

    People read the whole agreement before they accept it. Files of more than
    200 KB are refused: split the agreement or link to the details.
    """

    title = _("The file of an agreement is too large")


class AgreementTitleMissing(ConfigFileError):
    """The file of an agreement has no title.

    An agreement is Markdown and starts with its title as a heading of level 1,
    such as ``# Contributor License Agreement``. The site shows the agreement by
    this title everywhere. Add the heading to the file.
    """

    title = _("The agreement has no title")


class AgreementFileNotText(ConfigFileError):
    """The file of an agreement is not text in UTF-8.

    Agreements are shown as Markdown or as text. Save the file as UTF-8 text,
    such as Markdown with the extension ``.md``.
    """

    title = _("The file of an agreement is not text")
