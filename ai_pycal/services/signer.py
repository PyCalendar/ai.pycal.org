"""Sign an agreement: only a person on the page of the agreement can."""

import logging
import time

from django.conf import settings
from django.core import signing

from ai_pycal.actions import SignatureAdded
from ai_pycal.errors import (
    AgreementError,
    AgreementNotShown,
    AgreementVersionNotRequired,
    HandleMismatch,
    NotAccepted,
    SignedTooFast,
    SigningExpired,
)
from ai_pycal.models import AgreementVersion, PullRequest, Signature

from .identity import GitHubIdentity
from .pull_request_check import PullRequestCheck

log = logging.getLogger(__name__)
SALT = "ai_pycal.shown-agreement"


class Signer:
    """The signature of one person.

    The page of an agreement contains a token that says to whom it was shown and when
    (:meth:`shown_token`). Signing needs it, the ticked box and the typed handle: see
    docs/explanation/signing.rst.
    """

    def __init__(self, user, identity: GitHubIdentity):
        """The signer.

        Args:
            user: The user of the site.
            identity: The GitHub account of the user.
        """
        self.user = user
        self.identity = identity

    def shown_token(self, version: AgreementVersion) -> str:
        """The token that the agreement was shown to this person now.

        Args:
            version: The agreement.

        Returns:
            The signed token for the form.
        """
        return signing.dumps(
            {"v": version.pk, "g": self.identity.github_id, "t": time.time()}, salt=SALT
        )

    def check_shown(self, version: AgreementVersion, token: str) -> None:
        """Check that the agreement was shown to this person, long enough ago.

        Args:
            version: The agreement.
            token: The token of the form.

        Raises:
            AgreementNotShown: The token is missing or for something else.
            SigningExpired: It was shown too long ago.
            SignedTooFast: It was shown too shortly ago to read it.
        """
        try:
            data = signing.loads(token or "", salt=SALT)
        except signing.BadSignature as error:
            raise AgreementNotShown() from error
        if data.get("v") != version.pk or data.get("g") != self.identity.github_id:
            raise AgreementNotShown()
        age = time.time() - float(data.get("t", 0))
        if age > settings.SIGN_MAX_HOURS * 3600:
            raise SigningExpired()
        if age < settings.SIGN_MIN_SECONDS:
            raise SignedTooFast(f"{age:.0f} s")

    def sign(
        self, version: AgreementVersion, accepted: bool, handle: str, token: str
    ) -> tuple[Signature, bool]:
        """Sign an agreement and update the pull requests of this person.

        Args:
            version: The agreement.
            accepted: Whether the box was ticked.
            handle: The typed GitHub handle.
            token: The token of the page (:meth:`shown_token`).

        Returns:
            The signature and whether it is new.

        Raises:
            AgreementVersionNotRequired: No repository asks for this version.
            NotAccepted: The box was not ticked.
            HandleMismatch: The handle is not the one of the account.
            AgreementNotShown: The agreement was not shown before.
        """
        self.validate(version, accepted, handle, token)
        signature, created = Signature.objects.get_or_create(
            version=version,
            github_id=self.identity.github_id,
            defaults={"login": self.identity.login, "user": self.user},
        )
        if created:
            named = version.required_by.first()
            SignatureAdded(signature, named.name if named else version.path).run()
            self.update_pull_requests(version)
        return signature, created

    def validate(self, version: AgreementVersion, accepted: bool, handle: str, token: str) -> None:
        """Validate explicit consent before a page creates any signatures.

        Args:
            version: The version displayed on the signing page.
            accepted: Whether its acceptance checkbox was selected.
            handle: The contributor's typed GitHub handle.
            token: The page's signed display token.

        Raises:
            SigningError: Consent or the displayed agreement could not be verified.
        """
        if not version.required_by.filter(repository__active=True).exists():
            raise AgreementVersionNotRequired(str(version))
        self.check_shown(version, token)
        if not accepted:
            raise NotAccepted()
        if handle.strip().lstrip("@").lower() != self.identity.login.lower():
            raise HandleMismatch(f"@{handle.strip().lstrip('@')}")

    def update_pull_requests(self, version: AgreementVersion) -> list[PullRequest]:
        """Check the open pull requests of this person that need the agreement again.

        Errors of GitHub are logged: the pull requests are checked again on their next
        change.

        Args:
            version: The agreement that was signed.

        Returns:
            The pull requests that were checked.
        """
        pulls = list(
            PullRequest.objects.filter(
                open=True,
                author_github_id=self.identity.github_id,
                repository__active=True,
                repository__required_agreements__version=version,
            )
            .select_related("repository__installation")
            .distinct()
        )
        for pull in pulls:
            try:
                PullRequestCheck(pull).run()
            except AgreementError as error:
                log.warning("%s: %s %s", pull, error.code, error)
        return pulls
