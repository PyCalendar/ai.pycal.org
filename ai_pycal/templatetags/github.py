"""Links to GitHub with the mark of GitHub.

``{% github_link url label %}`` is the mark alone, for places where it is clear what it links
to, such as next to the title of a repository; ``label`` is its text for screen readers and
on hover. ``{% github_link url label text "button" %}`` shows the mark before ``text``.
"""

from django import template
from django.utils.html import format_html

from ai_pycal.github_mark import PATH

register = template.Library()


def mark() -> str:
    """The mark of GitHub as inline SVG, in the color of the text.

    Returns:
        The HTML, hidden from screen readers: the link has the label.
    """
    return format_html(
        '<svg class="icon github-mark" viewBox="0 0 16 16" width="16" height="16" '
        'aria-hidden="true" focusable="false"><path fill="currentColor" d="{}"/></svg>',
        PATH,
    )


@register.simple_tag
def github_link(url: str, label: str, text: str = "", css: str = "") -> str:
    """A link to GitHub with its mark.

    Args:
        url: The address on GitHub.
        label: What the link leads to, such as ``PyCalendar/icalendar on GitHub``.
        text: The visible text after the mark; "" for the mark alone.
        css: More classes of the link, such as ``button``.

    Returns:
        The HTML of the link; empty without an address.
    """
    if not url:
        return ""
    classes = f"github-link {css}".strip()
    if text:
        return format_html(
            '<a class="{}" href="{}" title="{}">{} <span>{}</span></a>',
            classes,
            url,
            label,
            mark(),
            text,
        )
    return format_html(
        '<a class="{} github-link-icon" href="{}" aria-label="{}" title="{}">{}</a>',
        classes,
        url,
        label,
        label,
        mark(),
    )
