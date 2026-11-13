"""The rights of the Django admin follow ``SITE_ADMINS`` at every request."""

from .services.identity import GitHubIdentity


class AdminRightsMiddleware:
    """Give the people of ``SITE_ADMINS`` the Django admin, and take it from the others.

    The sign-in does this too; this also applies a change of ``SITE_ADMINS`` to people who
    signed in before it.
    """

    def __init__(self, get_response):
        """The middleware.

        Args:
            get_response: The next step of Django.
        """
        self.get_response = get_response

    def __call__(self, request):
        """Keep the rights of the person, then answer.

        Args:
            request: The request.

        Returns:
            The answer.
        """
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            GitHubIdentity.keep_rights(user)
        return self.get_response(request)
