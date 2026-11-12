"""Handle the webhooks after answering GitHub, in the order they came."""

import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from ai_pycal.actions import Trigger, WebhookTrigger
from ai_pycal.errors import AgreementError
from ai_pycal.models import WebhookDelivery

from .webhook_handler import WebhookHandler

log = logging.getLogger(__name__)
MAX_ATTEMPTS = 3  # a delivery that stops the worker (such as a crash) is tried this often
KEEP_DAYS = 30  # handled deliveries are kept this long, to see what came


class WebhookQueue:
    """The deliveries that wait for the worker, and their handling."""

    @staticmethod
    def add(event: str, delivery: str, payload: dict) -> WebhookDelivery:
        """Keep a delivery whose signature was checked, for the worker.

        Args:
            event: ``X-GitHub-Event``.
            delivery: ``X-GitHub-Delivery``.
            payload: The JSON of the webhook.

        Returns:
            The delivery.
        """
        return WebhookDelivery.objects.create(event=event, delivery=delivery, payload=payload)

    @staticmethod
    def handle(event: str, delivery: str, payload: dict) -> tuple[str, AgreementError | None]:
        """Handle a webhook, recorded as a trigger of the log.

        Args:
            event: ``X-GitHub-Event``.
            delivery: ``X-GitHub-Delivery``.
            payload: The JSON of the webhook.

        Returns:
            What was done, and the error if the handler stopped with one.
        """
        with Trigger.start(
            "webhook", f"Webhook {event}", delivery=delivery, public=False
        ) as trigger:
            try:
                done = WebhookHandler(event, payload).handle()
            except AgreementError as error:
                # GitHub answered with an error or the configuration is broken: the pull
                # request is checked again on its next change or the regular update
                log.warning("webhook %s: %s %s", event, error.code, error)
                WebhookTrigger.complete(trigger, event, payload, error.code)
                return error.code, error
            WebhookTrigger.complete(trigger, event, payload, done)
            return done, None

    @classmethod
    def next(cls) -> WebhookDelivery | None:
        """Take the oldest delivery that is not handled yet.

        Returns:
            The delivery, with one more attempt counted, or None if none waits.
        """
        with transaction.atomic():
            found = (
                WebhookDelivery.objects.filter(finished__isnull=True)
                .order_by("received", "pk")
                .first()
            )
            if found is None:
                return None
            found.attempts += 1
            if found.attempts > MAX_ATTEMPTS:
                found.finished = timezone.now()
                found.done = f"given up after {MAX_ATTEMPTS} attempts"
                found.save(update_fields=["attempts", "finished", "done"])
                log.error("webhook %s given up after %d attempts", found, MAX_ATTEMPTS)
                return cls.next()
            found.save(update_fields=["attempts"])
            return found

    @classmethod
    def process(cls, delivery: WebhookDelivery) -> str:
        """Handle a delivery and mark it handled.

        Args:
            delivery: The delivery.

        Returns:
            What was done, or the code of the error.
        """
        done, _ = cls.handle(delivery.event, delivery.delivery, delivery.payload)
        delivery.done = done
        delivery.finished = timezone.now()
        delivery.save(update_fields=["done", "finished"])
        return done

    @classmethod
    def run_once(cls) -> int:
        """Handle every delivery that waits.

        Returns:
            How many were handled.
        """
        handled = 0
        while (delivery := cls.next()) is not None:
            try:
                cls.process(delivery)
            except Exception:  # a bug or a passing error of the database: tried again
                log.exception("webhook %s failed in attempt %d", delivery, delivery.attempts)
                continue
            handled += 1
        return handled

    @staticmethod
    def forget_old() -> int:
        """Delete handled deliveries older than :data:`KEEP_DAYS`.

        Returns:
            How many were deleted.
        """
        before = timezone.now() - timedelta(days=KEEP_DAYS)
        deleted, _ = WebhookDelivery.objects.filter(finished__lt=before).delete()
        return deleted

    @staticmethod
    def waiting() -> int:
        """How many deliveries wait for the worker.

        Returns:
            The number.
        """
        return WebhookDelivery.objects.filter(finished__isnull=True).count()
