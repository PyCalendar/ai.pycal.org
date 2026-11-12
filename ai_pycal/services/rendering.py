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


def markdown_title(text: str) -> str:
    r"""The title of an agreement: the text of its first heading of level 1.

    Args:
        text: The Markdown of the agreement.

    Returns:
        The title, without formatting; "" if there is none.

    Examples:
        >>> markdown_title("Intro\n\n# Contributor *License* Agreement\n\nText")
        'Contributor License Agreement'
        >>> markdown_title("## Only a subheading")
        ''
    """
    tokens = _markdown.parse(text)
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and token.tag == "h1":
            inline = tokens[index + 1]
            return "".join(
                child.content
                for child in inline.children or []
                if child.type in ("text", "code_inline")
            ).strip()[:200]
    return ""
