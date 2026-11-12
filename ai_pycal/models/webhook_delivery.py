"""A webhook of GitHub, kept until it is handled."""

from django.db import models


class WebhookDelivery(models.Model):
    """A delivery of a webhook whose signature was checked, waiting for the worker.

    The site answers GitHub at once and handles the delivery afterwards, in the order
    they came (``manage.py process_webhooks``): GitHub's time limit for an answer does not
    cut the work short, and deliveries survive a restart of the site.
    """

    event = models.CharField(max_length=100)
    delivery = models.CharField(max_length=100, blank=True)
    payload = models.JSONField()
    received = models.DateTimeField(auto_now_add=True, db_index=True)
    attempts = models.PositiveIntegerField(default=0)
    finished = models.DateTimeField(null=True, blank=True, db_index=True)
    done = models.TextField(blank=True)  # what the handler did, or the code of the error

    class Meta:
        ordering = ["received", "pk"]
        verbose_name_plural = "webhook deliveries"

    def __str__(self) -> str:
        return f"{self.event} {self.delivery}"
