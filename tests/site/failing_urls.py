"""The addresses of the site and one that fails, to test the page of server errors."""

from django.urls import path

from ai_pycal.urls import urlpatterns as site
from ai_pycal.views.errors import server_error


def fail(request):
    """Fail like an unexpected bug.

    Args:
        request: The request.

    Raises:
        RuntimeError: Always.
    """
    raise RuntimeError("a bug")


urlpatterns = [path("fail/", fail), *site]
handler500 = server_error
