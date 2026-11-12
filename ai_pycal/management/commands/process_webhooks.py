"""The worker of the webhooks: it handles them after the site answered GitHub."""

import time

from django.core.management.base import BaseCommand

from ai_pycal.services.webhook_queue import WebhookQueue


class Command(BaseCommand):
    """``manage.py process_webhooks``: runs next to the site, started by the container."""

    help = "Handle the webhooks that wait, in the order they came; --once stops when none waits."

    def add_arguments(self, parser):
        """The options.

        Args:
            parser: The parser of the arguments.
        """
        parser.add_argument("--once", action="store_true", help="stop when no webhook waits")
        parser.add_argument("--pause", type=float, default=1.0, help="seconds between looks")

    def handle(self, *args, **options):
        """Handle the deliveries; without --once, look for new ones forever.

        Args:
            *args: Not used.
            **options: ``once`` and ``pause``.
        """
        WebhookQueue.forget_old()
        while True:
            handled = WebhookQueue.run_once()
            if handled:
                self.stdout.write(f"{handled} webhooks handled")
            if options["once"]:
                return
            time.sleep(options["pause"])
