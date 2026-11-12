"""Errors of registering the GitHub App on the site, met by the people who run it.

The site registers its own GitHub App on ``/setup/github-app/``, see
:doc:`/how-to/github-app-site`. Each page of an error has details to copy for a
bug report.
"""

from django.utils.translation import gettext_lazy as _

from .base import AgreementError


class RegistrationError(AgreementError):
    """The GitHub App could not be registered.

    Start again on the page *Register GitHub App* of the site, as
    :doc:`/how-to/github-app-site` describes. If it fails again, copy the details
    of the page into a bug report.
    """

    title = _("The GitHub App could not be registered")
    guide = "how-to/github-app-site.html"
    guide_title = _("Register the GitHub App on the site")


class AppAlreadyRegistered(RegistrationError):
    """The site already has a GitHub App.

    A site has one GitHub App. Its settings come from the environment or from
    ``DATA_DIR/.env``, which the registration wrote. To use another app, remove
    the ``GITHUB_...`` settings from both and restart the site; the old app stays
    on GitHub until you delete it there.
    """

    title = _("The site already has a GitHub App")
    status = 409


class PrivateKeyFileExists(RegistrationError):
    """The file for the private key of the new app exists already.

    The registration writes the key to ``GITHUB_APP_PRIVATE_KEY_FILE``, such as
    ``/app/data/github-app.pem``, or to ``DATA_DIR/github-app.pem`` if that is
    not set, and never overwrites a file. A file there is the key of another app:
    set ``GITHUB_APP_ID`` and the other ``GITHUB_...`` settings of that app, or
    move the file away and register again.
    """

    title = _("A private key exists already")
    status = 409


class AppSettingsInEnvironment(RegistrationError):
    """Settings of a GitHub App are set in the environment.

    The settings of the environment take precedence over those the registration
    writes into the volume, so the site would mix two apps after a restart. The
    detail names the settings: ``GITHUB_APP_ID``, ``GITHUB_APP_SLUG``,
    ``GITHUB_CLIENT_ID``, ``GITHUB_SECRET``, ``GITHUB_WEBHOOK_SECRET`` or
    ``GITHUB_APP_PRIVATE_KEY``. Remove them or leave them empty, such as in
    ``.env``, restart the site and register again; or set all of them for an app
    that exists. ``GITHUB_APP_PRIVATE_KEY_FILE`` may stay: the registration
    writes the key there if the file does not exist.
    """

    title = _("Settings of a GitHub App are set in the environment")
    status = 409


class SetupCodeWrong(RegistrationError):
    """The setup code is missing or wrong.

    Only the people who run the site may register its GitHub App. The site writes
    the setup code into its log at every start while it has no app, and into
    ``DATA_DIR/github-app-setup-code``. ``manage.py github_app_setup_code`` shows
    it, for example with ``docker compose exec ai-pycal python manage.py
    github_app_setup_code``.
    """

    title = _("The setup code is wrong")
    status = 403


class InvalidAppName(RegistrationError):
    """The name of the GitHub App is empty or too long.

    GitHub needs a name of at most 34 characters that no other GitHub App has,
    such as ``ai-pycal-example-org``.
    """

    title = _("The name of the GitHub App is invalid")


class InvalidOrganization(RegistrationError):
    """The organization is not a GitHub login.

    Enter the login of the organization, such as ``PyCalendar``, or leave the field
    empty to register the app on your own account.
    """

    title = _("The organization is invalid")


class RegistrationExpired(RegistrationError):
    """The return from GitHub does not belong to a registration of this browser.

    The site gives each registration a secret state and checks it when GitHub
    returns. It was missing or different: the registration was started in another
    browser, the session expired, or the page was opened twice. Start again on the
    page *Register GitHub App*.
    """

    title = _("The registration does not belong to this browser")


class RegistrationCodeMissing(RegistrationError):
    """GitHub returned without the code of the new app.

    GitHub adds ``code`` to the address when the app was created. Without it, the
    registration was cancelled or did not finish on GitHub. Start again.
    """

    title = _("GitHub returned without a code")


class ManifestConversionFailed(RegistrationError):
    """GitHub refused to give the credentials of the new app.

    The site exchanged the code of the registration for the credentials of the
    app, and GitHub answered with the error shown in the details. A code is valid
    for an hour and only once: if it expired or was used, the app may already
    exist on GitHub. Delete it in the settings of the GitHub account and register
    again.
    """

    title = _("GitHub did not give the credentials of the app")
    status = 502


class RegistrationNotSaved(RegistrationError):
    """The credentials of the new app could not be written into the volume.

    The site writes them to ``DATA_DIR/.env`` and ``DATA_DIR/github-app.pem``.
    Check that the volume is mounted and writable for the site. The app exists on
    GitHub now: generate a private key and a client secret there and set the
    ``GITHUB_...`` settings yourself, see :doc:`/reference/settings`.
    """

    title = _("The credentials could not be saved")
    status = 500
