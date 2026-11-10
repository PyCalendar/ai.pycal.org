"""Errors of the webhooks that GitHub sends to the site.

GitHub shows them in the list of recent deliveries of the GitHub App, with the
status of the answer.
"""

from django.utils.translation import gettext_lazy as _

from .base import AgreementError


class WebhookError(AgreementError):
    """A webhook of GitHub could not be handled.

    See the recent deliveries in the advanced settings of the GitHub App for the
    answer, and :doc:`/how-to/github-app` for the setup.
    """

    title = _("The webhook could not be handled")
    guide = "how-to/github-app.html"
    guide_title = _("Create the GitHub App")


class WebhookSecretNotConfigured(WebhookError):
    """The site has no secret to check the webhooks with.

    Without ``GITHUB_WEBHOOK_SECRET`` anybody could send webhooks to the site, so
    they are refused. Set it to the webhook secret of the GitHub App.
    """

    title = _("The site has no webhook secret")
    status = 503


class WebhookSignatureMissing(WebhookError):
    """The webhook has no signature.

    GitHub signs every webhook with the secret of the app in the header
    ``X-Hub-Signature-256``. Set a webhook secret in the settings of the GitHub
    App.
    """

    title = _("The webhook has no signature")
    status = 401


class WebhookSignatureInvalid(WebhookError):
    """The signature of the webhook does not match the secret.

    The webhook secret of the GitHub App and ``GITHUB_WEBHOOK_SECRET`` of the
    site differ. Set both to the same value.
    """

    title = _("The signature of the webhook is invalid")
    status = 401


class WebhookPayloadInvalid(WebhookError):
    """The content of the webhook is not the JSON GitHub sends.

    Check that the content type of the webhook of the GitHub App is
    ``application/json``.
    """

    title = _("The content of the webhook is invalid")
