"""Errors of signing an agreement.

Agreements are signed by people on the page of the agreement, never by a
program; see :doc:`/explanation/signing`.
"""

from django.utils.translation import gettext_lazy as _

from .base import AgreementError


class SigningError(AgreementError):
    """The agreement could not be signed.

    Read the agreement on its page, tick the box and type your GitHub handle, as
    described in :doc:`/tutorial/sign`.
    """

    title = _("The agreement could not be signed")
    guide = "tutorial/sign.html"
    guide_title = _("Sign an agreement")


class NotAccepted(SigningError):
    """The box to accept the agreement was not ticked.

    Tick the box "I have read and accept this agreement" below the agreement to
    sign it.
    """

    title = _("You did not accept the agreement")


class HandleMismatch(SigningError):
    """The typed handle is not the GitHub handle you are signed in with.

    Type your GitHub handle, as shown in the menu, to confirm that you sign
    yourself. Upper and lower case do not matter, ``@`` can be left out.
    """

    title = _("The handle does not match your account")


class AgreementNotShown(SigningError):
    """The agreement was not shown to you before signing.

    An agreement can only be signed from its page, after it was shown. Open the
    agreement, read it and sign it there. Signing is not possible with a program.
    """

    title = _("The agreement was not shown before signing")


class AgreementVersionNotRequired(SigningError):
    """No repository asks for this version of the agreement.

    The agreement was changed since the page was opened, or the repositories
    that asked for it were removed. Open the agreement from the pull request
    again to sign the version that is asked for now.
    """

    title = _("This version of the agreement is not asked for")
    status = 404


class AgreementNotFound(SigningError):
    """There is no agreement with this address.

    Open the agreement from the pull request: the check of the site links to the
    agreements it needs.
    """

    title = _("The agreement was not found")
    status = 404


class PullRequestNotFound(SigningError):
    """The site does not know this pull request.

    The site knows the pull requests of the repositories that were added, from
    the moment they were added. Push a new commit to the pull request, or close
    and reopen it, so that GitHub tells the site about it.
    """

    title = _("The pull request was not found")
    status = 404


class SignedTooFast(SigningError):
    """The agreement was signed faster than it can be read.

    Signing is for people who read the agreement. Read it, then sign it again.
    The time is set by the project with ``sign-min-seconds`` in its configuration
    file, else by the site with ``SIGN_MIN_SECONDS``.
    """

    title = _("The agreement was signed too fast")


class SigningExpired(SigningError):
    """The page of the agreement was opened too long ago.

    Load the page of the agreement again and sign it. The time is set by
    ``SIGN_MAX_HOURS``.
    """

    title = _("The page of the agreement is too old")
