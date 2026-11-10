"""The webhook of the GitHub App."""

import json
import logging

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from ai_pycal.errors import AgreementError, WebhookError, WebhookPayloadInvalid
from ai_pycal.github.webhook_signature import verify
from ai_pycal.services.webhook_handler import WebhookHandler

log = logging.getLogger(__name__)


@csrf_exempt  # GitHub signs the webhooks instead
@require_POST
def webhook(request):
    """Receive a webhook of GitHub, check its signature and handle it.

    Args:
        request: The request of GitHub.

    Returns:
        JSON with what was done, or the error with its link to the documentation.
    """
    try:
        verify(
            settings.GITHUB_WEBHOOK_SECRET,
            request.body,
            request.headers.get("X-Hub-Signature-256"),
        )
        try:
            payload = json.loads(request.body)
        except ValueError as error:
            raise WebhookPayloadInvalid(str(error)) from error
        done = WebhookHandler(request.headers.get("X-GitHub-Event", ""), payload).handle()
    except WebhookError as error:
        return error_json(error)
    except AgreementError as error:
        # GitHub answered with an error or the configuration is broken: the pull request
        # is checked again on its next change; the delivery shows why
        log.warning("webhook: %s %s", error.code, error)
        return error_json(error, status=200)
    return JsonResponse({"done": done})


def error_json(error: AgreementError, status: int | None = None) -> JsonResponse:
    """An error as JSON, for the recent deliveries of the GitHub App.

    Args:
        error: The error.
        status: The HTTP status; that of the error by default.

    Returns:
        The answer.
    """
    return JsonResponse(
        {
            "error": error.code,
            "title": str(error.title),
            "detail": str(error),
            "documentation": error.docs_url(),
        },
        status=status or error.status,
    )
