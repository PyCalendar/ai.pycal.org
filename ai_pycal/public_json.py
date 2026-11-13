"""The public information of every page as JSON: ``/project/owner/name.json`` and so on.

The JSON of a page is at its address with ``.json`` instead of the last ``/``; that of the
start page is ``/index.json``. It holds what a visitor who is not signed in sees: the request
is answered as for such a visitor, also if it carries the cookie of a session. Every answer
allows other sites to read it with JavaScript (CORS).
"""

from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse, JsonResponse
from django.urls import Resolver404, resolve

from .services.public_data import page_address

# the pages that have JSON: those that are public
JSON_PAGES = {
    "home",
    "about",
    "licenses",
    "projects",
    "owner_projects",
    "contributor",
    "owner_log",
    "project_log",
    "pull_log",
    "contributor_log",
    "history",
    "project",
    "project_status",
    "project_pull",
    "agreement",
    "changes",
}
CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
}
READING = {"GET", "HEAD"}


class PublicJsonMiddleware:
    """Answer ``<page>.json`` with the public information of the page, readable by any site."""

    def __init__(self, get_response):
        """The middleware.

        Args:
            get_response: The next step of Django.
        """
        self.get_response = get_response

    def __call__(self, request):
        """Answer the request; ``<page>.json`` as JSON with the headers of CORS.

        Args:
            request: The request.

        Returns:
            The answer.
        """
        path = request.path_info
        if not path.endswith(".json"):
            return self.get_response(request)
        try:
            resolve(path)  # an address of its own, such as the status of a policy
        except Resolver404:
            pass
        else:
            return self.cors(self.get_response(request))
        page = page_address(path)
        try:
            known = resolve(page).url_name in JSON_PAGES
        except Resolver404:
            known = False
        if not known:
            return self.cors(self.failure(404, "NotFound", "This page has no JSON."))
        request.path_info = page
        request.public_json = True
        if request.method == "OPTIONS":
            return self.cors(HttpResponse(status=204))
        if request.method not in READING:
            response = self.failure(405, "MethodNotAllowed", "The JSON can only be read.")
            response["Allow"] = CORS["Access-Control-Allow-Methods"]
            return self.cors(response)
        return self.cors(self.as_json(self.get_response(request)))

    def process_view(self, request, view, args, kwargs):
        """Answer ``<page>.json`` as for a visitor who is not signed in.

        Args:
            request: The request.
            view: The view.
            args: Its arguments.
            kwargs: Its keyword arguments.

        Returns:
            None: the view answers.
        """
        if getattr(request, "public_json", False):
            request.user = AnonymousUser()
        return None

    @staticmethod
    def failure(status: int, code: str, detail: str) -> JsonResponse:
        """A failure as JSON.

        Args:
            status: The HTTP status.
            code: The name of the failure.
            detail: What happened.

        Returns:
            ``error``, ``status`` and ``detail``.
        """
        return JsonResponse({"error": code, "status": status, "detail": detail}, status=status)

    def as_json(self, response):
        """Keep JSON; turn the pages of failures and redirects into JSON.

        A redirect means that the page needs a sign-in, so it has no public JSON.

        Args:
            response: The answer of the view.

        Returns:
            JSON.
        """
        if response.get("Content-Type", "").startswith("application/json"):
            return response
        if 300 <= response.status_code < 400:
            return self.failure(404, "NotPublic", "This page needs a sign-in: it has no JSON.")
        return self.failure(
            response.status_code, response.reason_phrase.replace(" ", ""), response.reason_phrase
        )

    @staticmethod
    def cors(response):
        """Allow every site to read the answer with JavaScript.

        Args:
            response: The answer.

        Returns:
            The answer, with the headers of CORS.
        """
        for name, value in CORS.items():
            response[name] = value
        return response
