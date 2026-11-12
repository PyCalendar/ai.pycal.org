"""The webhooks are answered at once and handled afterwards by the worker, in order."""

import pytest
from django.core.management import call_command

from ai_pycal.models import LogTrigger, WebhookDelivery
from ai_pycal.services import webhook_queue
from ai_pycal.services.webhook_queue import MAX_ATTEMPTS, WebhookQueue
from tests.conftest import REPOSITORY, pull_payload, send_webhook

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def queued(settings):
    settings.WEBHOOK_QUEUE = True


def test_the_queue_is_the_default():
    from ai_pycal import settings as site_settings

    assert site_settings.WEBHOOK_QUEUE


def test_a_webhook_is_answered_at_once_and_handled_by_the_worker(client, github, repository):
    response = send_webhook(client, "pull_request", pull_payload(github, 1))
    assert response.status_code == 202
    delivery = WebhookDelivery.objects.get(pk=response.json()["queued"])
    assert not repository.pull_requests.exists()  # nothing done yet
    call_command("process_webhooks", "--once")
    delivery.refresh_from_db()
    assert delivery.finished is not None and delivery.done == "checked #1"
    assert "cla-missing" in github.labels[(REPOSITORY, 1)]
    trigger = LogTrigger.objects.get(kind="webhook")
    assert trigger.summary.startswith("Pull request #1 opened") and trigger.public


def test_the_worker_keeps_the_order(client, github, repository):
    import copy

    opened = copy.deepcopy(pull_payload(github, 1))
    closed = copy.deepcopy(opened)
    closed["action"] = "closed"
    closed["pull_request"]["state"] = "closed"
    send_webhook(client, "pull_request", opened)
    send_webhook(client, "pull_request", closed)
    assert WebhookQueue.waiting() == 2
    assert WebhookQueue.run_once() == 2
    assert not repository.pull_requests.get(number=1).open


def test_refused_webhooks_are_not_queued(client):
    response = send_webhook(client, "ping", {}, secret="wrong")
    assert response.status_code == 401
    assert response.json()["error"] == "WebhookSignatureInvalid"
    assert not WebhookDelivery.objects.exists()
    assert LogTrigger.objects.get().summary == "Refused webhook ping: WebhookSignatureInvalid"


def test_a_payload_that_is_no_mapping_is_refused_at_once(client):
    response = send_webhook(client, "ping", [1, 2])
    assert response.status_code == 400
    assert response.json()["error"] == "WebhookPayloadInvalid"
    assert not WebhookDelivery.objects.exists()


def test_errors_of_github_are_kept_with_the_delivery(client, github, repository):
    payload = pull_payload(github, 1)
    send_webhook(client, "pull_request", payload)
    github.fail_with = 500
    WebhookQueue.run_once()
    delivery = WebhookDelivery.objects.get()
    assert delivery.done == "GitHubError" and delivery.finished is not None


def test_a_delivery_that_breaks_the_worker_is_given_up(client, monkeypatch):
    send_webhook(client, "ping", {"zen": "x"})
    send_webhook(client, "ping", {"zen": "y"})

    def broken(event, delivery, payload):
        if payload["zen"] == "x":
            raise RuntimeError("a bug")
        return "pong", None

    monkeypatch.setattr(WebhookQueue, "handle", staticmethod(broken))
    assert WebhookQueue.run_once() == 1  # the second one is handled; the first given up
    first, second = WebhookDelivery.objects.order_by("pk")
    assert first.attempts == MAX_ATTEMPTS + 1 and first.done.startswith("given up")
    assert second.done == "pong"


def test_deliveries_survive_a_restart(client):
    send_webhook(client, "ping", {"zen": "x"})
    # the site restarts before the worker took it: it waits in the database
    assert WebhookQueue.waiting() == 1
    call_command("process_webhooks", "--once")
    assert WebhookQueue.waiting() == 0


def test_old_deliveries_are_forgotten(client):
    from datetime import timedelta

    from django.utils import timezone

    send_webhook(client, "ping", {"zen": "x"})
    WebhookQueue.run_once()
    WebhookDelivery.objects.update(
        finished=timezone.now() - timedelta(days=webhook_queue.KEEP_DAYS + 1)
    )
    send_webhook(client, "ping", {"zen": "y"})  # waits: kept
    assert WebhookQueue.forget_old() == 1
    assert WebhookDelivery.objects.count() == 1


def test_the_worker_runs_in_the_container():
    from pathlib import Path

    start = (Path(__file__).parents[2] / "docker" / "start-service.sh").read_text()
    assert "manage.py process_webhooks" in start
