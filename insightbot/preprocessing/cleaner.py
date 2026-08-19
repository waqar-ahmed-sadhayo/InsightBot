"""HTML cleaning and text normalization.

Two responsibilities, kept separate so extraction can use either:
  - clean_soup(html)   -> BeautifulSoup with junk tags/nodes removed
                          (still has structure, needed for the extraction
                          scoring heuristics)
  - normalize_text(s)  -> unicode/whitespace-normalized plain string
                          (used on every text value pulled out of the soup)
"""
from __future__ import annotations

import re
import unicodedata

from bs4 import BeautifulSoup, Comment

# Tags that never contain article content. NOTE: <header> is deliberately
# NOT blanket-stripped here -- it's the standard HTML5 wrapper for an
# article's <h1>+byline (<article><header><h1>...), so removing it
# outright breaks title extraction on a large fraction of real sites.
# Nav-link-heavy headers still won't pollute the *body* because the body
# scorer discounts high link-density blocks.
_JUNK_TAGS = [
    "script", "style", "noscript", "iframe", "svg", "form",
    "nav", "footer", "aside", "button", "input", "select", "textarea",
]

# Class/id substrings (lowercased) commonly used for boilerplate blocks
# across English, Arabic, and Russian news sites. Substring match keeps
# this generic across unseen markup (e.g. "site-nav", "nav-primary",
# "related-articles", "socialshare", "قائمة" [menu, ar]). Deliberately
# excludes the bare word "header" (too broad -- matches "article-header",
# "story-header", which usually wrap the title, not boilerplate); only
# site-chrome-specific header variants are listed.
_BOILERPLATE_HINTS = [
    "nav", "menu", "sidebar", "footer", "site-header", "page-header",
    "masthead", "global-header", "banner", "advert", "ad-slot", "-ad-", "ads-",
    "comment", "share", "social", "related", "recommend", "subscribe", "newsletter",
    "cookie", "popup", "modal", "breadcrumb", "pagination", "tag-list", "widget",
    "promo", "sponsor", "author-box", "byline-social", "toolbar", "search-box",
]


def _looks_boilerplate(tag) -> bool:
    ident = " ".join([tag.get("id", ""), " ".join(tag.get("class", []) or [])]).lower()
    if not ident.strip():
        return False
    return any(hint in ident for hint in _BOILERPLATE_HINTS)


# A hint substring can appear inside a legitimate content wrapper's class
# name for reasons unrelated to boilerplate -- e.g. BBC's
# "ContainerWithSidebarWrapper" (the *main content* column of a two-column
# layout, named after the sidebar it sits *next to*) contains "sidebar" but
# wraps the entire article body. Rather than trying to out-guess every
# compound class name, skip the decompose when the flagged tag already
# holds enough prose-like paragraph text that it's almost certainly real
# content, not chrome -- true boilerplate (nav, ads, share widgets, cookie
# banners) never accumulates this much paragraph text.
_SUBSTANTIAL_MIN_PARAGRAPH_LEN = 25
_SUBSTANTIAL_CONTENT_CHARS = 400


def _has_substantial_content(tag) -> bool:
    total = 0
    for p in tag.find_all("p"):
        text = p.get_text(strip=True)
        if len(text) >= _SUBSTANTIAL_MIN_PARAGRAPH_LEN:
            total += len(text)
            if total >= _SUBSTANTIAL_CONTENT_CHARS:
                return True
    return False


def clean_soup(html: str) -> BeautifulSoup:
    """Parses HTML and strips scripts/styles/comments/nav/ads/boilerplate
    in place. Never raises on malformed HTML: BeautifulSoup's built-in
    'html.parser' tolerates broken markup, and every removal step is
    independently guarded.
    """
    soup = BeautifulSoup(html or "", "html.parser")

    for tag_name in _JUNK_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
        comment.extract()

    for tag in soup.find_all(True):
        try:
            if _looks_boilerplate(tag) and not _has_substantial_content(tag):
                tag.decompose()
        except Exception:
            continue

    return soup


def normalize_text(text: str) -> str:
    """NFC-normalize unicode (important for Arabic combining marks and
    Russian text copied from varied encodings) and collapse whitespace,
    while preserving paragraph breaks as single newlines.
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    # Collapse runs of spaces/tabs but keep paragraph breaks.
    text = re.sub(r"[ \t ​]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()


def element_text(tag) -> str:
    """Extracts and normalizes visible text from a bs4 tag."""
    if tag is None:
        return ""
    raw = tag.get_text(separator=" ", strip=True)
    return normalize_text(raw)
