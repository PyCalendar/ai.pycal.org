"""A page as HTML, or its public information as JSON at ``<page>.json``."""

from django.http import JsonResponse
from django.shortcuts import render


def wants_json(request) -> bool:
    """Whether the request asks for the JSON of a page, see :mod:`ai_pycal.public_json`.

    Args:
        request: The request.

    Returns:
        True for ``<page>.json``.
    """
    return getattr(request, "public_json", False)


def page(request, template: str, context: dict, data, status: int = 200):
    """Answer with the page, or with its data for ``<page>.json``.

    Args:
        request: The request.
        template: The template of the page.
        context: The context of the template.
        data: A function without arguments that returns the public information of the
            page; called only for the JSON.
        status: The HTTP status.

    Returns:
        The page or the JSON.
    """
    if wants_json(request):
        return JsonResponse(data(), status=status, json_dumps_params={"ensure_ascii": False})
    return render(request, template, context, status=status)
