"""Errors of setting up repositories, met by their administrators."""

from django.utils.translation import gettext_lazy as _

from .base import AgreementError


class SetupError(AgreementError):
    """The repository could not be set up.

    Follow :doc:`/tutorial/admin` to install the GitHub App and add the
    repository.
    """

    title = _("The repository could not be set up")
    guide = "tutorial/admin.html"
    guide_title = _("Set up a repository")


class RepositoryNotFound(SetupError):
    """The site does not know this repository.

    Add the repository on the page Setup first. Only repositories of
    installations that you administer are shown.
    """

    title = _("The repository was not found")
    status = 404


class InvalidNotificationEmail(SetupError):
    """The email address for notifications is not valid.

    The site writes to this address when the GitHub App needs new permissions.
    Enter an address such as ``maintainers@example.org``, or leave it empty.
    """

    title = _("The email address is invalid")


class NotRepositoryAdmin(SetupError):
    """You do not administer this repository on GitHub.

    Only people with the role admin or maintain of a repository can add it,
    change it or remove it. Ask an administrator of the repository.
    """

    title = _("You do not administer this repository")
    status = 403
