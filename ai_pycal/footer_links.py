"""The extra links of the About page, set with ``FOOTER_LINKS`` for each site."""

from ai_pycal.errors import InvalidFooterLink

DEFAULT = "pycal.org=https://pycal.org"


def parse_footer_links(value: str) -> list[tuple[str, str]]:
    """The links of ``FOOTER_LINKS``: ``Title=URL`` entries, separated by commas.

    Args:
        value: The setting, such as ``pycal.org=https://pycal.org,Blog=https://example.org/``.
            Empty: no extra links.

    Returns:
        The title and address of each link, in order.

    Raises:
        InvalidFooterLink: An entry has no title, or its address is not http or https.

    Examples:
        >>> parse_footer_links(DEFAULT)
        [('pycal.org', 'https://pycal.org')]
        >>> parse_footer_links(" A = https://a.example/?x=1 , B=http://b.example ")
        [('A', 'https://a.example/?x=1'), ('B', 'http://b.example')]
        >>> parse_footer_links("")
        []
    """
    links = []
    for entry in value.split(","):
        if not entry.strip():
            continue
        title, _, url = (part.strip() for part in entry.partition("="))
        if not title or not url.startswith(("https://", "http://")):
            raise InvalidFooterLink(f"FOOTER_LINKS: {entry.strip()!r}")
        links.append((title, url))
    return links
