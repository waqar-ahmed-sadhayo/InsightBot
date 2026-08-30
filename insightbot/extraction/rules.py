"""Rule-based (non-ML) extraction of {title, body, date} from a cleaned
BeautifulSoup document.

Algorithm summary (see README.md "How the extraction rules were derived"
for the full writeup):

  TITLE: score every <h1>/<h2> candidate by tag weight + title-like
  class/id hints + document position + length sanity bounds; take the
  highest scorer; fall back to og:title, then <title>.

  BODY: score every <p> (density-based, Boilerpipe/Readability style:
  text length minus link density) and roll each <p>'s score up into its
  parent and grandparent container; the container with the highest
  aggregate score is the article body; concatenate its <p> text in
  document order. Falls back to the single longest <p> block if no
  container scores well (the literal "longest contiguous block" rule).

  DATE: structured meta tags first (article:published_time, itemprop,
  <time datetime>, etc.), then a regex scan of visible text supporting
  English, Arabic, and Russian date formats.

Every step is wrapped so a failure on one field never prevents extracting
the others -- this module must not raise for "normal" bad/unusual HTML.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin

from bs4 import Tag

from insightbot.extraction import dates as date_utils
from insightbot.extraction.domain_rules import DomainRule
from insightbot.preprocessing.cleaner import element_text, normalize_text

MIN_TITLE_LEN = 8
MAX_TITLE_LEN = 220
MIN_PARAGRAPH_LEN = 25
MAX_LINK_DENSITY = 0.5


@dataclass
class ExtractedArticle:
    title: Optional[str]
    body: Optional[str]
    date: Optional[str]
    language: str
    source_url: str
    image: Optional[str] = None
    title_method: str = "none"
    body_method: str = "none"
    date_method: str = "none"
    image_method: str = "none"
    warnings: list = field(default_factory=list)


# --------------------------------------------------------------------------
# TITLE
# --------------------------------------------------------------------------

_TITLE_HINT_WORDS = ("title", "headline", "heading", "post-title", "entry-title")


def _title_candidate_score(tag: Tag, index: int) -> int:
    score = 30 if tag.name == "h1" else 10
    ident = f"{tag.get('id', '')} {' '.join(tag.get('class', []) or [])}".lower()
    if any(w in ident for w in _TITLE_HINT_WORDS):
        score += 15
    ancestor_names = {p.name for p in tag.parents if isinstance(p, Tag)}
    if "header" in ancestor_names or "article" in ancestor_names:
        score += 8
    score += max(0, 10 - index)  # earlier candidates get a small edge
    return score


def extract_title(soup, rule: DomainRule) -> tuple[Optional[str], str]:
    if rule.title_selector:
        try:
            el = soup.select_one(rule.title_selector)
            text = element_text(el)
            if text:
                return text, "domain_rule"
        except Exception:
            pass

    candidates = []
    for i, tag in enumerate(soup.find_all(["h1", "h2"])):
        text = element_text(tag)
        if not text or not (MIN_TITLE_LEN <= len(text) <= MAX_TITLE_LEN):
            continue
        candidates.append((_title_candidate_score(tag, i), text))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1], "heuristic_h1_h2"

    og = soup.find("meta", attrs={"property": "og:title"})
    if og and og.get("content"):
        return normalize_text(og["content"]), "og_title"

    if soup.title and soup.title.string:
        text = normalize_text(str(soup.title.string))
        if text:
            # strip a trailing " | Site Name" / " - Site Name" suffix
            for sep in (" | ", " – ", " — ", " - "):
                if sep in text:
                    text = text.split(sep)[0].strip()
                    break
            return text, "title_tag"

    return None, "none"


# --------------------------------------------------------------------------
# BODY
# --------------------------------------------------------------------------

def _link_density(tag: Tag, text_len: int) -> float:
    link_len = sum(len(a.get_text(strip=True)) for a in tag.find_all("a"))
    return link_len / max(text_len, 1)


def _score_containers(soup) -> dict:
    scores: dict[int, tuple[float, Tag]] = {}

    def bump(container: Tag, amount: float):
        if container is None or not isinstance(container, Tag):
            return
        key = id(container)
        prev = scores.get(key, (0.0, container))
        scores[key] = (prev[0] + amount, container)

    for p in soup.find_all(["p", "div"]):
        text = element_text(p)
        if len(text) < MIN_PARAGRAPH_LEN:
            continue
        if _link_density(p, len(text)) > MAX_LINK_DENSITY:
            continue
        commas = sum(text.count(c) for c in (",", "،", "，"))
        base = 1 + commas * 0.5 + min(len(text) / 100, 5)

        parent = p.parent
        if parent is not None and isinstance(parent, Tag):
            bump(parent, base)
            grandparent = parent.parent
            if grandparent is not None and isinstance(grandparent, Tag):
                bump(grandparent, base * 0.5)

    return scores


def _gather_paragraphs(container: Tag) -> str:
    parts = []
    for p in container.find_all("p"):
        text = element_text(p)
        if len(text) >= MIN_PARAGRAPH_LEN and _link_density(p, len(text)) <= MAX_LINK_DENSITY:
            parts.append(text)
    if not parts:
        # container itself may hold text directly (div-based body with no <p>s)
        text = element_text(container)
        if text:
            parts = [text]
    return "\n\n".join(parts)


def extract_body(soup, rule: DomainRule) -> tuple[Optional[str], str]:
    if rule.body_selector:
        try:
            el = soup.select_one(rule.body_selector)
            if el is not None:
                text = _gather_paragraphs(el) or element_text(el)
                if text:
                    return text, "domain_rule"
        except Exception:
            pass

    scores = _score_containers(soup)
    if scores:
        best_score, best_container = max(scores.values(), key=lambda t: t[0])
        if best_score > 0:
            text = _gather_paragraphs(best_container)
            if text and len(text) >= MIN_PARAGRAPH_LEN:
                return text, "density_scored_container"

    # Literal fallback per spec: longest single contiguous <p>/<div> block.
    longest = ""
    for p in soup.find_all(["p", "div"]):
        text = element_text(p)
        if len(text) > len(longest):
            longest = text
    if longest:
        return longest, "longest_block_fallback"

    return None, "none"


# --------------------------------------------------------------------------
# DATE
# --------------------------------------------------------------------------

_META_DATE_CANDIDATES = [
    ("meta", {"property": "article:published_time"}, "content"),
    ("meta", {"property": "og:published_time"}, "content"),
    ("meta", {"name": "date"}, "content"),
    ("meta", {"name": "pubdate"}, "content"),
    ("meta", {"name": "publish-date"}, "content"),
    ("meta", {"name": "publication_date"}, "content"),
    ("meta", {"itemprop": "datePublished"}, "content"),
    ("time", {"itemprop": "datePublished"}, "datetime"),
]


def extract_date(soup, rule: DomainRule) -> tuple[Optional[str], str]:
    if rule.date_selector:
        try:
            el = soup.select_one(rule.date_selector)
            if el is not None:
                raw = el.get(rule.date_attr) if rule.date_attr else element_text(el)
                parsed = date_utils.parse_date(raw)
                if parsed:
                    return parsed, "domain_rule"
        except Exception:
            pass

    for tag_name, attrs, attr in _META_DATE_CANDIDATES:
        el = soup.find(tag_name, attrs=attrs)
        if el is not None:
            raw = el.get(attr) or element_text(el)
            parsed = date_utils.parse_date(raw)
            if parsed:
                return parsed, "meta_tag"

    time_el = soup.find("time")
    if time_el is not None:
        raw = time_el.get("datetime") or element_text(time_el)
        parsed = date_utils.parse_date(raw)
        if parsed:
            return parsed, "time_tag"

    sample = element_text(soup)[:5000]
    parsed = date_utils.scan_text_for_date(sample)
    if parsed:
        return parsed, "regex_scan"

    return None, "none"


# --------------------------------------------------------------------------
# IMAGE
# --------------------------------------------------------------------------

_IMAGE_META_CANDIDATES = [
    ("meta", {"property": "og:image"}, "content"),
    ("meta", {"property": "og:image:url"}, "content"),
    ("meta", {"name": "twitter:image"}, "content"),
    ("meta", {"name": "twitter:image:src"}, "content"),
]


def extract_image(soup, url: str, rule: DomainRule) -> tuple[Optional[str], str]:
    """A real cover image pulled from the page's own metadata -- never a
    fabricated/stock photo. Most sites publish og:image for social-share
    previews, which is exactly the "representative image" a reader would
    expect next to the headline."""
    if rule.image_selector:
        try:
            el = soup.select_one(rule.image_selector)
            src = el.get("src") if el is not None else None
            if src:
                return urljoin(url, src.strip()), "domain_rule"
        except Exception:
            pass

    for tag_name, attrs, attr in _IMAGE_META_CANDIDATES:
        el = soup.find(tag_name, attrs=attrs)
        if el is not None:
            raw = el.get(attr)
            if raw and raw.strip():
                return urljoin(url, raw.strip()), "meta_tag"

    return None, "none"


# --------------------------------------------------------------------------
# ORCHESTRATOR
# --------------------------------------------------------------------------

def extract_article(soup, url: str, language: str, rule: DomainRule) -> ExtractedArticle:
    """Runs title/body/date extraction independently, so a failure in one
    never blocks the others."""
    warnings = []

    try:
        title, title_method = extract_title(soup, rule)
    except Exception as exc:
        title, title_method = None, "error"
        warnings.append(f"title extraction failed: {exc}")

    try:
        body, body_method = extract_body(soup, rule)
    except Exception as exc:
        body, body_method = None, "error"
        warnings.append(f"body extraction failed: {exc}")

    try:
        date, date_method = extract_date(soup, rule)
    except Exception as exc:
        date, date_method = None, "error"
        warnings.append(f"date extraction failed: {exc}")

    try:
        image, image_method = extract_image(soup, url, rule)
    except Exception as exc:
        image, image_method = None, "error"
        warnings.append(f"image extraction failed: {exc}")

    return ExtractedArticle(
        title=title,
        body=body,
        date=date,
        language=language,
        source_url=url,
        image=image,
        title_method=title_method,
        body_method=body_method,
        date_method=date_method,
        image_method=image_method,
        warnings=warnings,
    )
