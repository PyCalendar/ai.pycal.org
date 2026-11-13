"""Show the text of an agreement as HTML."""

import re

from django.utils.html import escape
from django.utils.safestring import SafeString, mark_safe
from markdown_it import MarkdownIt

MARKDOWN = (".md", ".markdown")
# CommonMark without HTML of its own: an agreement can not bring scripts into the page
_markdown = MarkdownIt("commonmark", {"html": False, "linkify": False})
# a block of metadata at the start of a Markdown file, such as of Jekyll or Hugo
FRONT_MATTER = re.compile(
    r"\A\ufeff?---[ \t]*\r?\n.*?^(?:---|\.\.\.)[ \t]*(?:\r?\n|\Z)", re.S | re.M
)


def without_front_matter(text: str) -> str:
    r"""The Markdown without the block of metadata between ``---`` lines at its start.

    Args:
        text: The Markdown.

    Returns:
        The text that people read.

    Examples:
        >>> without_front_matter("---\nlayout: page\n---\n# Title\n")
        '# Title\n'
        >>> without_front_matter("Text\n\n---\n\nMore\n")
        'Text\n\n---\n\nMore\n'
    """
    return FRONT_MATTER.sub("", text, count=1)


def _same_title(first: str, second: str) -> bool:
    """Whether two titles are the same, apart from spaces and case."""
    return " ".join(first.split()).casefold() == " ".join(second.split()).casefold()


def _heading_text(inline) -> str:
    """The text of a heading, without formatting."""
    return "".join(
        child.content for child in inline.children or [] if child.type in ("text", "code_inline")
    ).strip()


def render(text: str, path: str, title: str = "") -> SafeString:
    r"""The agreement as HTML: Markdown for ``.md`` files, else preformatted text.

    Markdown loses its front matter, and its first heading if that is the *title* that the
    page already shows above it.

    Args:
        text: The text of the agreement.
        path: The path of the file, for its kind.
        title: The title that the page shows above the text.

    Returns:
        The HTML.

    Examples:
        >>> render("# Title <script>", "a.md")
        '<h1>Title &lt;script&gt;</h1>\n'
        >>> render("---\nlang: en\n---\n# AI  Policy\n\nText", "a.md", title="AI policy")
        '<p>Text</p>\n'
        >>> render("# Other\n", "a.md", title="AI Policy")
        '<h1>Other</h1>\n'
        >>> render("<b>", "a.txt")
        '<pre class="agreement-text">&lt;b&gt;</pre>'
    """
    if path.lower().endswith(MARKDOWN):
        tokens = _markdown.parse(without_front_matter(text))
        if (
            title
            and len(tokens) >= 3
            and tokens[0].type == "heading_open"
            and tokens[0].tag == "h1"
            and _same_title(_heading_text(tokens[1]), title)
        ):
            tokens = tokens[3:]  # the heading: open, its text, close
        html = _markdown.renderer.render(tokens, _markdown.options, {})
        return mark_safe(html)  # noqa: S308 - html is off
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
        >>> markdown_title("---\n# a comment of YAML\n---\n# The title\n")
        'The title'
    """
    tokens = _markdown.parse(without_front_matter(text))
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and token.tag == "h1":
            return _heading_text(tokens[index + 1])[:200]
    return ""
