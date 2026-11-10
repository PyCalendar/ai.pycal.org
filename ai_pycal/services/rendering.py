"""Show the text of an agreement as HTML."""

from django.utils.html import escape
from django.utils.safestring import SafeString, mark_safe
from markdown_it import MarkdownIt

MARKDOWN = (".md", ".markdown")
# CommonMark without HTML of its own: an agreement can not bring scripts into the page
_markdown = MarkdownIt("commonmark", {"html": False, "linkify": False})


def render(text: str, path: str) -> SafeString:
    r"""The agreement as HTML: Markdown for ``.md`` files, else preformatted text.

    Args:
        text: The text of the agreement.
        path: The path of the file, for its kind.

    Returns:
        The HTML.

    Examples:
        >>> render("# Title <script>", "a.md")
        '<h1>Title &lt;script&gt;</h1>\n'
        >>> render("<b>", "a.txt")
        '<pre class="agreement-text">&lt;b&gt;</pre>'
    """
    if path.lower().endswith(MARKDOWN):
        return mark_safe(_markdown.render(text))  # noqa: S308 - html is off
    return mark_safe(f'<pre class="agreement-text">{escape(text)}</pre>')  # noqa: S308
