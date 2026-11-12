"""Times for people: how long ago, like GitHub, with the exact time on hover.

``{% when value %}`` renders a ``<time>`` element: the text says how long ago (or the date, for
times older than :data:`RELATIVE_DAYS`), and the title shows the exact time in UTC. Without
JavaScript this is what people see. ``static/local-time.js`` then shows the exact time in the
local time of the browser and keeps the relative text current; the rules are the same.
"""

from datetime import UTC, datetime

from django import template
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext, ngettext

register = template.Library()

RELATIVE_DAYS = 30  # older times show their date, as on GitHub


def ago(value: datetime, now: datetime) -> str:
    """How long ago a time was, in words.

    Args:
        value: The time.
        now: The time of the page.

    Returns:
        Such as ``just now``, ``5 minutes ago``, ``yesterday`` or ``on 2026-10-01``.

    Examples:
        >>> now = datetime(2026, 11, 12, 15, 0, tzinfo=UTC)
        >>> ago(datetime(2026, 11, 12, 14, 59, 40, tzinfo=UTC), now)
        'just now'
        >>> ago(datetime(2026, 11, 12, 12, 0, tzinfo=UTC), now)
        '3 hours ago'
        >>> ago(datetime(2026, 11, 11, 9, 0, tzinfo=UTC), now)
        'yesterday'
        >>> ago(datetime(2026, 10, 1, 9, 0, tzinfo=UTC), now)
        'on 2026-10-01'
    """
    seconds = (now - value).total_seconds()
    if seconds < 45:
        return gettext("just now")
    minutes = round(seconds / 60)
    if minutes < 60:
        return ngettext("%(count)d minute ago", "%(count)d minutes ago", minutes) % {
            "count": minutes
        }
    hours = round(seconds / 3600)
    if hours < 24:
        return ngettext("%(count)d hour ago", "%(count)d hours ago", hours) % {"count": hours}
    days = round(seconds / 86400)
    if days < 2:
        return gettext("yesterday")
    if days < RELATIVE_DAYS:
        return ngettext("%(count)d day ago", "%(count)d days ago", days) % {"count": days}
    return gettext("on %(date)s") % {"date": value.astimezone(UTC).strftime("%Y-%m-%d")}


@register.simple_tag
def when(value: datetime | None) -> str:
    """A ``<time>`` element: how long ago, the exact time in UTC on hover.

    Args:
        value: The time, aware; or None.

    Returns:
        The HTML; empty for None.
    """
    if value is None:
        return ""
    utc = value.astimezone(UTC)
    return format_html(
        '<time class="when" datetime="{}" title="{}">{}</time>',
        utc.isoformat(timespec="seconds").replace("+00:00", "Z"),
        utc.strftime("%Y-%m-%d %H:%M UTC"),
        ago(utc, timezone.now()),
    )
