"""Links to the documentation next to things: a question mark in a circle.

``{% help_link url label %}`` opens the page of the documentation in a new tab; ``label`` says
what it explains, for screen readers and on hover.
"""

from django import template
from django.utils.html import format_html
from django.utils.translation import gettext

register = template.Library()


@register.simple_tag
def help_link(url: str, label: str) -> str:
    """A link to the documentation as a question mark in a circle, opening a new tab.

    Args:
        url: The page of the documentation.
        label: What the page explains, such as ``Email for new permissions``.

    Returns:
        The HTML of the link; empty without an address.
    """
    if not url:
        return ""
    title = gettext("Help: %(label)s (opens in a new tab)") % {"label": label}
    return format_html(
        '<a class="help-link" href="{}" target="_blank" rel="noopener" title="{}" '
        'aria-label="{}"><span aria-hidden="true">?</span></a>',
        url,
        title,
        title,
    )
