"""Errors of the answers of GitHub and of the GitHub App."""

from django.utils.translation import gettext_lazy as _

from .base import AgreementError


class GitHubError(AgreementError):
    """GitHub answered with an error.

    The detail contains the answer of GitHub. Try again later; if it stays,
    report a bug with the detail.
    """

    title = _("GitHub answered with an error")
    status = 502
    guide = "how-to/report-bug.html"


class GitHubUnreachable(GitHubError):
    """GitHub could not be reached.

    The network or GitHub is down. See https://www.githubstatus.com/ and try
    again later.
    """

    title = _("GitHub could not be reached")
    status = 503


class GitHubRateLimited(GitHubError):
    """GitHub allows no more requests for now.

    The GitHub App has used all requests GitHub allows in an hour. The pull
    requests are checked again on their next change; try again in an hour.
    """

    title = _("GitHub allows no more requests for now")
    status = 503


class GitHubAnswerNotJSON(GitHubError):
    """GitHub answered with something that is not JSON.

    This happens when GitHub is partly down or a proxy answered. Try again later.
    """

    title = _("GitHub answered with something unreadable")


class GitHubFileHistoryInvalid(GitHubError):
    """GitHub returned an invalid commit in an agreement file's history.

    The site cannot identify the agreement's last edit safely. Try again later;
    if the problem continues, report a bug with the repository and file path.
    """

    title = _("GitHub returned an invalid file history")


class GitHubAppNotConfigured(AgreementError):
    """The site has no GitHub App.

    The people who run the site register it on the site with the button
    *Register GitHub App* (:doc:`/how-to/github-app-site`), or set
    ``GITHUB_APP_ID``, ``GITHUB_APP_SLUG``, ``GITHUB_APP_PRIVATE_KEY``,
    ``GITHUB_CLIENT_ID``, ``GITHUB_SECRET`` and ``GITHUB_WEBHOOK_SECRET`` as
    described in :doc:`/how-to/github-app`.
    """

    title = _("The site has no GitHub App")
    status = 503
    register_app = True  # the page of the error offers to register the app on the site
    guide = "how-to/github-app.html"
    guide_title = _("Create the GitHub App")


class SignInNotConfigured(GitHubAppNotConfigured):
    """Signing in with GitHub is not configured.

    The site signs people in with an OAuth app, which only tells who they are and
    their email addresses. The people who run the site create it on GitHub and
    enter it on the page ``/setup/oauth-app/`` with the setup code of the log, or
    set ``GITHUB_OAUTH_CLIENT_ID`` and ``GITHUB_OAUTH_SECRET``, as described in
    :ref:`oauth-app`. For development, put them into ``.env``: ``make run`` reads
    it.
    """

    title = _("Signing in with GitHub is not configured")
    guide = "how-to/github-app-site.html#oauth-app"
    guide_title = _("The OAuth app for signing in")


class InvalidPrivateKey(GitHubAppNotConfigured):
    """The private key of the GitHub App can not be read.

    ``GITHUB_APP_PRIVATE_KEY`` contains the whole PEM file that GitHub generated
    for the app, from ``-----BEGIN RSA PRIVATE KEY-----`` to the end, or
    ``GITHUB_APP_PRIVATE_KEY_FILE`` names that file. Generate a new key on the
    page of the app if it was lost.
    """

    title = _("The private key of the GitHub App is invalid")


class InstallationNotFound(AgreementError):
    """GitHub does not know this installation of the GitHub App.

    The app was uninstalled, or the address of the setup was changed. Install
    the app again from the page Setup.
    """

    title = _("The installation of the GitHub App was not found")
    status = 404
    guide = "tutorial/admin.html"
    guide_title = _("Set up a repository")


class InstallationNotYours(AgreementError):
    """You can not administer this installation of the GitHub App.

    Only people who can manage the GitHub App on an account or organization,
    such as its owners, can add its repositories. Ask an owner to install the
    app, or to make you an app manager of the organization.
    """

    title = _("You can not administer this installation")
    status = 403
    guide = "tutorial/admin.html"
    guide_title = _("Set up a repository")


class RepositoryNotInstalled(AgreementError):
    """The GitHub App is not installed on this repository.

    Repositories can only be added if the app can read them and label their pull
    requests. Add the repository to the installation on GitHub, then refresh the
    page Setup.
    """

    title = _("The GitHub App is not installed on this repository")
    status = 404
    guide = "tutorial/admin.html"
    guide_title = _("Set up a repository")


class MissingPermissions(AgreementError):
    """The GitHub App lacks permissions it needs.

    A new version of the site needs more permissions than were accepted when the
    app was installed. The administrators of the installation got an email: open
    the installation on GitHub and accept the new permissions. Which permissions
    are needed is listed in :doc:`/reference/permissions`.
    """

    title = _("The GitHub App lacks permissions")
    status = 403
    guide = "reference/permissions.html"
    guide_title = _("Permissions of the GitHub App")


class GitHubNotFound(GitHubError):
    """GitHub does not know what was asked for, or the GitHub App may not read it.

    The repository, the branch, the tag or the file does not exist, or it is
    private and the app is not installed on it.
    """

    title = _("GitHub did not find it")
    status = 404


class GitHubLoginExpired(AgreementError):
    """You are not signed in with GitHub.

    The site asks GitHub, with its app, which repositories you manage, by your
    GitHub account. Accounts of the site without GitHub, and sign ins that
    GitHub no longer accepts, cannot be used for that. Sign out and sign in with
    GitHub again.
    """

    title = _("Your sign in with GitHub has expired")
    status = 401
    guide = "tutorial/admin.html"
    guide_title = _("Set up a repository")


class CannotWriteLabels(GitHubError):
    """The GitHub App could not update the pull request's labels.

    Check that the app is installed on this repository with pull_requests:
    write permission and is not suspended. Accept any pending permission update
    on GitHub, then refresh the project on Setup to retry its open pull requests.
    """

    title = _("The GitHub App cannot write pull request labels")
    status = 403
    guide = "reference/permissions.html"
