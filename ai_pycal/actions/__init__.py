"""The actions of the site and the log of why they happened.

Every effect of the site, such as a label added to a pull request, is an :class:`Action`: it
does the effect and records itself, with its reason, in the current :class:`Trigger`, such as
the webhook or the person that caused it. The pages ``/logs/...`` show them.
"""

from .action import Action
from .agreement_changed import AgreementChanged
from .configuration_read import ConfigurationRead
from .email_sent import EmailSent
from .label_added import LabelAdded
from .label_removed import LabelRemoved
from .signature_added import SignatureAdded
from .signature_removed import SignatureRemoved
from .status_set import StatusSet
from .trigger import Trigger
from .webhook_trigger import WebhookTrigger

__all__ = [
    "Action",
    "AgreementChanged",
    "ConfigurationRead",
    "EmailSent",
    "LabelAdded",
    "LabelRemoved",
    "SignatureAdded",
    "SignatureRemoved",
    "StatusSet",
    "Trigger",
    "WebhookTrigger",
]
