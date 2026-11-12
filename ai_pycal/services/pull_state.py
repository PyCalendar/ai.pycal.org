"""The state of a pull request for people, with its color."""

from .pull_request_check import PullRequestCheck

LABELS = {
    "signed": "All agreements signed",
    "missing": "Agreements to sign",
    "optional": "Optional agreements to sign",
    "merged": "Merged",
    "closed": "Closed",
}


class PullState:
    """Whether a pull request is open and signed, merged or closed.

    ``signed`` (green): open and every agreement signed; ``missing`` (red): open and a
    needed agreement is not signed; ``optional`` (yellow): open and only optional ones are
    not signed; ``merged`` (purple); ``closed`` (red): closed without merge.
    """

    @staticmethod
    def of(pull) -> str:
        """The state of a pull request.

        Args:
            pull: The pull request.

        Returns:
            ``signed``, ``missing``, ``optional``, ``merged`` or ``closed``.
        """
        if pull.merged:
            return "merged"
        if not pull.open:
            return "closed"
        states = PullRequestCheck(pull).states()
        if any(state.required and not state.signed for state in states):
            return "missing"
        if any(not state.signed for state in states):
            return "optional"
        return "signed"

    @classmethod
    def annotate(cls, pulls) -> list:
        """Pull requests with ``state`` and ``state_label``, for the templates.

        Args:
            pulls: The pull requests.

        Returns:
            The pull requests.
        """
        found = list(pulls)
        for pull in found:
            pull.state = cls.of(pull)
            pull.state_label = LABELS[pull.state]
        return found
