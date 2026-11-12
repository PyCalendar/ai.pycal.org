"""An email of the site: only in the global log, as addresses are private."""

from django.core.mail import send_mail

from .action import Action


class EmailSent(Action):
    """Send an email and record it, without the addresses, in the global log."""

    kind = "email"
    public = False

    def __init__(self, subject: str, body: str, recipients: list[str], repository=None):
        """The email.

        Args:
            subject: The subject.
            body: The text.
            recipients: The addresses.
            repository: The repository it is about, or None.
        """
        super().__init__(repository=repository)
        self.subject, self.body, self.recipients = subject, body, recipients

    def perform(self) -> None:
        """Send the email; ``sent`` is the number of emails sent."""
        self.sent = send_mail(self.subject, self.body, None, self.recipients)

    def text(self) -> str:
        """Such as ``Email to 2 addresses: New permissions for ai.pycal.org``."""
        return f"Email to {len(self.recipients)} addresses: {self.subject}"
