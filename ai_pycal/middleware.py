"""Show the errors of the site with their title, detail and link to the documentation."""

import logging

from allauth.socialaccount.models import SocialApp
from django.http import JsonResponse
from django.shortcuts import render

from .errors import AgreementError, SignInNotConfigured, UnexpectedError

log = logging.getLogger(__name__)


class ErrorPageMiddleware:
    """Render :class:`~ai_pycal.errors.AgreementError` as a page that explains it."""

    def __init__(self, get_response):
        """The middleware.

        Args:
            get_response: The next step of Django.
        """
        self.get_response = get_response

    def __call__(self, request):
        """Answer the request.

        Args:
            request: The request.

        Returns:
            The answer.
        """
        return self.get_response(request)

    def process_exception(self, request, exception):
        """Show errors of the site; others are left to Django.

        Args:
            request: The request.
            exception: What was raised.

        Returns:
            The page of the error; None for other exceptions.
        """
        if isinstance(exception, SocialApp.DoesNotExist):
            # allauth has no GitHub client: the OAuth app is not set
            exception = SignInNotConfigured("GITHUB_OAUTH_CLIENT_ID, GITHUB_OAUTH_SECRET")
        if not isinstance(exception, AgreementError):
            return None
        if isinstance(exception, UnexpectedError):
            log.exception("unexpected error", exc_info=exception)
        if getattr(request.resolver_match, "url_name", "") == "policy_json" or getattr(
            request, "public_json", False
        ):
            return JsonResponse(
                {
                    "error": exception.code,
                    "title": str(exception.title),
                    "detail": str(exception),
                    "documentation": exception.docs_url(),
                },
                status=exception.status,
            )
        return error_page(request, exception)


def error_page(request, error: AgreementError, status: int | None = None):
    """The page of an error.

    Args:
        request: The request.
        error: The error.
        status: The HTTP status; that of the error by default.

    Returns:
        The answer.
    """
    return render(request, "ai_pycal/error.html", {"error": error}, status=status or error.status)
