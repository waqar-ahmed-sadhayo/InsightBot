from insightbot.ingestion.fetcher import _looks_like_html


def test_looks_like_html_accepts_normal_html():
    assert _looks_like_html("<html><body><p>Hello world</p></body></html>") is True


def test_looks_like_html_rejects_garbled_binary_body():
    # Observed in practice: a 200 response whose body is mojibake from a
    # mis-decoded compressed payload (see fetcher.py docstring). Should be
    # treated as a fetch failure, not "successfully fetched empty page".
    garbled = "�" * 50 + "Yd��^=d" + "�" * 50
    assert _looks_like_html(garbled) is False


def test_looks_like_html_rejects_empty_body():
    assert _looks_like_html("") is False


def test_looks_like_html_tolerates_a_few_replacement_characters():
    # A handful of mis-decoded characters in otherwise normal HTML
    # shouldn't trip the garbled-response check.
    text = "<html><body><p>Caf� with a stray glyph</p></body></html>"
    assert _looks_like_html(text) is True
