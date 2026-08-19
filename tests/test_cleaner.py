from insightbot.preprocessing.cleaner import clean_soup, normalize_text


def test_clean_soup_strips_script_and_style():
    html = "<html><body><script>alert(1)</script><style>.a{}</style><p>Hello</p></body></html>"
    soup = clean_soup(html)
    assert soup.find("script") is None
    assert soup.find("style") is None
    assert soup.find("p").get_text() == "Hello"


def test_clean_soup_strips_nav_and_boilerplate_classed_divs():
    html = """
    <html><body>
      <nav>Home | About</nav>
      <div class="site-footer">Copyright 2026</div>
      <div class="related-articles">Read also...</div>
      <article><p>Real content here.</p></article>
    </body></html>
    """
    soup = clean_soup(html)
    assert soup.find("nav") is None
    assert soup.find("div", class_="site-footer") is None
    assert soup.find("div", class_="related-articles") is None
    assert "Real content" in soup.get_text()


def test_clean_soup_keeps_content_wrapper_whose_class_merely_mentions_sidebar():
    # Regression: a class like "ContainerWithSidebarWrapper" (a real-world
    # BBC pattern -- the main content column of a two-column layout, named
    # after the sidebar it sits next to) must not be wiped out just because
    # "sidebar" is a substring of its class name.
    html = """
    <html><body>
      <article>
        <div class="ContainerWithSidebarWrapper">
          <p>This is the first real paragraph of the article, with enough
          text to look like genuine prose rather than a nav label.</p>
          <p>This is the second real paragraph, continuing the story with
          more substantive detail so the total easily clears the threshold.</p>
          <p>And a third paragraph to be sure the accumulated content length
          comfortably exceeds the substantial-content guard in the cleaner.</p>
        </div>
      </article>
    </body></html>
    """
    soup = clean_soup(html)
    assert len(soup.find_all("p")) == 3
    assert "first real paragraph" in soup.get_text()


def test_clean_soup_never_raises_on_malformed_html():
    broken_html = "<html><body><div><p>Unclosed paragraph<div>Nested badly</p></div>"
    soup = clean_soup(broken_html)  # should not raise
    assert soup is not None


def test_normalize_text_collapses_whitespace_and_normalizes_unicode():
    text = "Hello   \t  world\n\n\n\nSecond   paragraph"
    result = normalize_text(text)
    assert result == "Hello world\n\nSecond paragraph"


def test_normalize_text_handles_empty_input():
    assert normalize_text("") == ""
    assert normalize_text(None) == ""
