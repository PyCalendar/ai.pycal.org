"""Private account preferences."""

from django.conf import settings
from django.db import models


class Profile(models.Model):
    """Email preferences belong to a person's account, never to their public page."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    email_notifications = models.BooleanField(default=True)
