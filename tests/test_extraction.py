from insightbot.extraction.domain_rules import DomainRule
from insightbot.extraction.rules import extract_article
from insightbot.preprocessing.cleaner import clean_soup

EMPTY_RULE = DomainRule()


def _extract(html, url="https://unseen-site.example/a", language="en"):
    soup = clean_soup(html)
    return extract_article(soup, url, language, EMPTY_RULE)


def test_generic_extraction_picks_h1_title_and_longest_article_body():
    html = """
    <html><head><title>Site Name</title></head>
    <body>
      <nav>Home About Contact</nav>
      <header><h1>Local Council Approves New Budget Plan</h1></header>
      <div class="sidebar"><p>Sponsored link text here that should be ignored.</p></div>
      <article>
        <p>The council voted 7-2 in favor of the new annual budget on Tuesday, after months of debate.</p>
        <p>Officials say the plan prioritizes road repairs and school funding over the next fiscal year.</p>
        <p>Residents can review the full budget document on the city website starting next week.</p>
      </article>
      <div class="related-articles"><p>Read also: last year's budget summary and analysis piece.</p></div>
    </body></html>
    """
    result = _extract(html)
    assert result.title == "Local Council Approves New Budget Plan"
    assert "council voted 7-2" in result.body
    assert "road repairs" in result.body
    assert "Sponsored link" not in (result.body or "")
    assert "Read also" not in (result.body or "")


def test_generic_extraction_handles_unfamiliar_div_based_structure():
    # No <article> tag, no clear class hints -- must still generalize.
    html = """
    <html><body>
      <div id="wrap">
        <div id="story-head"><h2 class="headline">Markets Rally After Rate Decision</h2></div>
        <div id="story">
          <p>Stocks climbed sharply on Thursday after the central bank held interest rates steady.</p>
          <p>Analysts said the decision removed a major source of uncertainty for investors this quarter.</p>
        </div>
      </div>
    </body></html>
    """
    result = _extract(html)
    assert result.title == "Markets Rally After Rate Decision"
    assert "Stocks climbed sharply" in result.body


def test_date_extraction_from_meta_tag():
    html = """
    <html><head>
      <meta property="article:published_time" content="2026-03-05T10:00:00Z">
    </head><body><h1>Some Headline About Nothing In Particular</h1>
    <article><p>Body text long enough to count as the main content block here.</p></article>
    </body></html>
    """
    result = _extract(html)
    assert result.date == "2026-03-05"
    assert result.date_method == "meta_tag"


def test_extraction_never_raises_on_empty_or_junk_html():
    result = _extract("")
    assert result.title is None
    assert result.body is None

    result = _extract("<html><body><div><span>just some fragments</span></div></body></html>")
    assert result.title is None  # no h1/h2, body still shouldn't crash


def test_domain_rule_overrides_generic_heuristic():
    html = """
    <html><body>
      <h1>Wrong Auto-detected Title</h1>
      <div class="official-title">The Correct Title From CSS Selector</div>
      <div class="official-body"><p>The correct body text selected via CSS override.</p></div>
    </body></html>
    """
    rule = DomainRule(title_selector="div.official-title", body_selector="div.official-body")
    soup = clean_soup(html)
    result = extract_article(soup, "https://example.com/a", "en", rule)
    assert result.title == "The Correct Title From CSS Selector"
    assert "correct body text" in result.body
