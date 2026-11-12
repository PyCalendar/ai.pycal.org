"""The webhook of the GitHub App."""

import json

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from ai_pycal.actions import Trigger
from ai_pycal.errors import AgreementError, WebhookError, WebhookPayloadInvalid
from ai_pycal.github.webhook_signature import verify
from ai_pycal.services.webhook_queue import WebhookQueue


@csrf_exempt  # GitHub signs the webhooks instead
@require_POST
def webhook(request):
    """Receive a webhook of GitHub, check its signature and queue it.

    The signature is checked at once, so that GitHub sees refused deliveries. The work is
    done afterwards by ``manage.py process_webhooks``, so that GitHub's time limit for the
    answer does not matter; with ``WEBHOOK_QUEUE = False`` it is done before the answer.

    Args:
        request: The request of GitHub.

    Returns:
        JSON with the queued delivery or what was done, or the error with its link to the
        documentation.
    """
    event = request.headers.get("X-GitHub-Event", "")
    delivery = request.headers.get("X-GitHub-Delivery", "")[:100]
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
        if not isinstance(payload, dict):
            raise WebhookPayloadInvalid(type(payload).__name__)
    except WebhookError as error:
        # refused webhooks are triggers of the global log only
        with Trigger.start(
            "webhook", f"Refused webhook {event}: {error.code}", delivery=delivery, public=False
        ):
            pass
        return error_json(error)
    if settings.WEBHOOK_QUEUE:
        queued = WebhookQueue.add(event, delivery, payload)
        return JsonResponse({"queued": queued.pk}, status=202)
    done, error = WebhookQueue.handle(event, delivery, payload)
    if error is not None:
        if isinstance(error, WebhookError):
            return error_json(error)
        return error_json(error, status=200)  # the delivery shows why
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
