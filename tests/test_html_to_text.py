"""Tests for html_to_text."""

from receipt_sweep.imap_client import html_to_text


def test_strips_style_and_script():
    html = (
        "<html><head><style>body { color: red; }</style></head>"
        "<body><script>alert('x');</script><p>Hello</p></body></html>"
    )
    text = html_to_text(html)
    assert "color: red" not in text
    assert "alert" not in text
    assert "Hello" in text


def test_block_tags_become_newlines():
    html = "<p>First line</p><p>Second line</p>"
    text = html_to_text(html)
    assert "First line" in text
    assert "Second line" in text
    # The two paragraphs must not be run together on one line.
    assert "First lineSecond line" not in text
    lines = [ln for ln in text.splitlines() if ln.strip()]
    assert lines == ["First line", "Second line"]


def test_br_creates_newline():
    html = "Line one<br>Line two"
    text = html_to_text(html)
    assert "Line one" in text
    assert "Line two" in text
    assert "Line oneLine two" not in text


def test_whitespace_collapsed():
    html = "<p>lots    of\t\tspace   here</p>"
    text = html_to_text(html)
    assert "lots of space here" in text


def test_consecutive_blank_lines_removed():
    html = "<div>A</div><div></div><div></div><div>B</div>"
    text = html_to_text(html)
    # No more than one blank line in a row.
    assert "\n\n\n" not in text
