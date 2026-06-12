"""Extract meaningful links from HTML email bodies.

Many job-alert emails (Glassdoor, hirist.tech, LinkedIn, etc.) embed their
apply links only in the HTML part and provide a useless ``body_text``
(e.g. ``"Please Enable Javascript"`` or ``null``).  This module parses the
HTML, extracts anchor tags, decodes common tracking-URL wrappers, and
returns a structured text representation that the LLM can use to identify
job listings and their apply links.
"""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from urllib.parse import unquote


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_links_from_html(
    html_content: str,
    *,
    max_links: int = 50,
) -> list[tuple[str, str]]:
    """Parse HTML and return ``(link_text, href)`` tuples for each ``<a>`` tag.

    Tracking wrappers and percent-encoded URLs are decoded so the LLM
    receives the final destination URL whenever possible.

    Args:
        html_content: Raw HTML string from the email body.
        max_links: Cap on the number of links returned to avoid token bloat.

    Returns:
        A list of ``(visible_text, href)`` pairs.  Empty strings are
        possible when the anchor has no text content or no ``href``.
    """
    parser = _LinkParser()
    try:
        parser.feed(html_content)
    except Exception:
        pass
    raw_links = parser.links[:max_links]

    cleaned: list[tuple[str, str]] = []
    for text, href in raw_links:
        decoded_href = _decode_tracking_url(href)
        cleaned.append((text.strip(), decoded_href.strip()))
    return cleaned


# Regex for plain-text URLs in angle brackets like <http://example.com>
_ANGLE_BRACKET_URL_RE = re.compile(r"<(https?://[^\s>]+)>")
# Regex for bare URLs in plain text
_BARE_URL_RE = re.compile(r"(?<!\S)(https?://[^\s<>\"]+)")


def extract_links_from_text(
    text: str,
    *,
    max_links: int = 50,
) -> list[tuple[str, str]]:
    """Extract URLs from plain text, handling angle-bracket and bare formats.

    Args:
        text: Plain text email body.
        max_links: Cap on the number of links returned.

    Returns:
        A list of ``("", url)`` pairs (no anchor text available in plain text).
    """
    seen: set[str] = set()
    results: list[tuple[str, str]] = []

    # First: angle-bracket URLs take priority
    for match in _ANGLE_BRACKET_URL_RE.finditer(text):
        url = _decode_tracking_url(match.group(1))
        if url not in seen:
            seen.add(url)
            results.append(("", url))
            if len(results) >= max_links:
                return results

    # Then: bare URLs
    for match in _BARE_URL_RE.finditer(text):
        url = _decode_tracking_url(match.group(1))
        if url not in seen:
            seen.add(url)
            results.append(("", url))
            if len(results) >= max_links:
                return results

    return results


def build_link_context(
    links: list[tuple[str, str]],
    *,
    max_chars: int = 6_000,
) -> str:
    """Format extracted links into a compact text block for LLM prompts.

    Each link is rendered as ``- <text> | <url>`` on its own line.  The
    output is truncated to ``max_chars`` to prevent excessively long prompts.

    Args:
        links: ``(link_text, href)`` tuples from :func:`extract_links_from_html`.
        max_chars: Maximum character length of the returned string.

    Returns:
        A newline-separated string of link entries, or an empty string when
        there are no links to render.
    """
    if not links:
        return ""

    lines: list[str] = []
    total_len = 0
    for text, href in links:
        if not href or not href.startswith(("http://", "https://")):
            continue
        entry = f"- {text} | {href}" if text else f"- {href}"
        if total_len + len(entry) > max_chars:
            break
        lines.append(entry)
        total_len += len(entry) + 1  # +1 for newline
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tracking-URL decoder
# ---------------------------------------------------------------------------

# Common patterns: URL-within-URL tracking redirects.
# e.g. https://postoffice.hirist.tech/CL0/https:%2F%2Fwww.hirist.tech%2Fj%2F.../...
# e.g. https://click.glassdoor.com/redirect?url=https%3A%2F%2F...
_TRACKING_URL_RE = re.compile(
    r"https?://[^/]+/.+?(https?(?:%3A|:)(?:%2F|/)(?:%2F|/)\S+)",
    re.IGNORECASE,
)


def _decode_tracking_url(url: str) -> str:
    """Attempt to unwrap a tracking redirect and return the destination URL.

    Applies percent-decoding iteratively (some wrappers double-encode)
    and extracts an embedded ``https://`` destination when the URL matches
    common job-board tracking patterns.

    Falls back to the original URL (percent-decoded once) when no embedded
    URL is found.
    """
    if not url:
        return url

    # First, percent-decode the entire URL to normalise
    decoded = unquote(unquote(url))

    # Try to find an embedded target URL
    match = _TRACKING_URL_RE.match(decoded)
    if match:
        target = match.group(1)
        target = unquote(unquote(target))
        # Strip trailing tracking fragments (e.g. /1/0101019ea...)
        # Only strip if the target itself looks like a complete URL
        if target.startswith("http"):
            return target

    return decoded


# ---------------------------------------------------------------------------
# Lightweight HTML link parser
# ---------------------------------------------------------------------------


class _LinkParser(HTMLParser):
    """Accumulate ``<a href="...">text</a>`` pairs from an HTML document."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._current_href: str | None = None
        self._current_text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            href = ""
            for name, value in attrs:
                if name.lower() == "href" and value:
                    href = html.unescape(value)
                    break
            self._current_href = href
            self._current_text_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._current_href is not None:
            text = " ".join(self._current_text_parts).strip()
            self.links.append((text, self._current_href))
            self._current_href = None
            self._current_text_parts = []

    def handle_data(self, data: str) -> None:
        if self._current_href is not None:
            self._current_text_parts.append(data.strip())
