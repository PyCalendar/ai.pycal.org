"""The signature with which GitHub signs its webhooks."""

import hashlib
import hmac

from ai_pycal.errors import (
    WebhookSecretNotConfigured,
    WebhookSignatureInvalid,
    WebhookSignatureMissing,
)


def sign(secret: str, body: bytes) -> str:
    """The signature of a body, as GitHub sends it in ``X-Hub-Signature-256``.

    Args:
        secret: The webhook secret.
        body: The body of the request.

    Returns:
        ``sha256=`` and the HMAC in hexadecimal digits.

    Examples:
        >>> sign("secret", b"{}")[:15]
        'sha256=77325902'
    """
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def verify(secret: str, body: bytes, signature: str | None) -> None:
    """Check that GitHub sent the body.

    Args:
        secret: The webhook secret of the site.
        body: The body of the request.
        signature: The header ``X-Hub-Signature-256``.

    Raises:
        WebhookSecretNotConfigured: The site has no secret.
        WebhookSignatureMissing: There is no signature.
        WebhookSignatureInvalid: The signature does not match.
    """
    if not secret:
        raise WebhookSecretNotConfigured("GITHUB_WEBHOOK_SECRET")
    if not signature:
        raise WebhookSignatureMissing("X-Hub-Signature-256")
    if not hmac.compare_digest(sign(secret, body), signature):
        raise WebhookSignatureInvalid("X-Hub-Signature-256")
