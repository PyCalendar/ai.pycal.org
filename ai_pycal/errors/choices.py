"""Errors in policy choices and changes made by contributors."""

from django.utils.translation import gettext_lazy as _

from .config_file import ConfigFileError
from .signing import SigningError


class InvalidMandatory(ConfigFileError):
    """An agreement's mandatory flag is not a boolean.

    Use the YAML value true or false without quotes for mandatory. Mandatory
    agreements apply to every pull request regardless of the selected choice.
    """

    title = _("The mandatory flag must be true or false")


class InvalidChoices(ConfigFileError):
    """The choices field is not a list of mappings.

    Write choices as a YAML list. Each entry needs a unique name, a description,
    and a nonempty list of agreement identifiers, as in the configuration guide.
    """

    title = _("The choices must be a list of choices")


class InvalidChoiceField(ConfigFileError):
    """A choice has a missing or invalid field.

    Give each choice a name, a Markdown description and a nonempty agreements
    list. Its default flag must be true or false. The detail names the field.
    """

    title = _("A choice field is missing or invalid")


class UnknownChoiceAgreement(ConfigFileError):
    """A choice references an agreement that is not defined.

    Every identifier in a choice's agreements list must be a key under
    agreements in the same configuration. Correct the spelling or define it.
    """

    title = _("A choice refers to an unknown agreement")


class DuplicateChoice(ConfigFileError):
    """Two choices have the same name or normalized identifier.

    Use distinct choice names. Names become lowercase identifiers with words
    separated by hyphens, so punctuation alone cannot distinguish two choices.
    """

    title = _("Choice names must be distinct")


class MultipleDefaultChoices(ConfigFileError):
    """More than one choice is marked as the project default.

    Set default to true for at most one choice. Contributors may choose their
    own project default and override it on individual pull requests.
    """

    title = _("Only one choice can be the project default")


class ChoiceNotFound(SigningError):
    """The selected choice is no longer offered by this project.

    Reload the pull request page and select one of the current choices. The
    project configuration may have changed since the form was opened.
    """

    title = _("The choice is not available")
    status = 404


class NotPullRequestAuthor(SigningError):
    """Only the pull request author may change its policy choice or sign for it.

    Sign in with the GitHub account that authored this pull request. Maintainers
    can view signatures but cannot select policies or sign on another person's behalf.
    """

    title = _("Only the pull request author can change its agreements")
    status = 403


class ChoiceNotAMapping(InvalidChoiceField):
    """A choices list entry is not a mapping of fields.

    Replace the entry with a mapping containing name, description and agreements.
    Every choice must define its own fields below the list marker.
    """

    title = _("A choice is not a mapping")


class InvalidChoiceName(InvalidChoiceField):
    """A choice name is empty, too long or cannot form a stable identifier.

    Use a name of at most 200 characters with letters or digits. Its normalized
    lowercase hyphenated identifier must contain between one and fifty characters.
    """

    title = _("The choice name is invalid")


class InvalidChoiceDescription(InvalidChoiceField):
    """A choice lacks a nonempty Markdown description.

    Add description as a text value explaining the choice to contributors.
    Put multiline Markdown in a YAML block scalar introduced with a vertical bar.
    """

    title = _("The choice needs a Markdown description")


class InvalidChoiceAgreements(InvalidChoiceField):
    """A choice does not list the agreements it requires.

    Set agreements to a nonempty YAML list of policy identifiers, such as
    agreements: [ai-policy]. Each identifier must exist under agreements.
    """

    title = _("The choice needs a list of agreements")


class InvalidChoiceDefault(InvalidChoiceField):
    """A choice's default flag is not a YAML boolean.

    Set default to true or false without quotes. Leave the field out to use
    false. At most one configured choice may have default set to true.
    """

    title = _("The choice default must be true or false")
