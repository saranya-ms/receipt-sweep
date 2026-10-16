"""Tests for IMAP search-criteria construction and escaping."""

from receipt_sweep.imap_client import IMAPClient, _imap_quote


def test_imap_quote_plain():
    assert _imap_quote("receipts@store.com") == '"receipts@store.com"'


def test_imap_quote_escapes_double_quote():
    assert _imap_quote('He said "hi"') == '"He said \\"hi\\""'


def test_imap_quote_escapes_backslash():
    assert _imap_quote("a\\b") == '"a\\\\b"'
    # Backslash is escaped before the quote, so order is preserved.
    assert _imap_quote('a\\"b') == '"a\\\\\\"b"'


def test_imap_quote_strips_newlines():
    assert "\n" not in _imap_quote("line1\nline2")
    assert "\r" not in _imap_quote("line1\r\nline2")


class _RecordingConn:
    """Fake IMAP connection that captures the SEARCH criteria."""

    def __init__(self):
        self.search_criteria = None

    def select(self, mailbox, readonly=True):
        return ("OK", [b"1"])

    def search(self, charset, criteria):
        self.search_criteria = criteria
        # Return no matches so search_emails stops before any fetch.
        return ("OK", [b""])


def _run_search(**kwargs):
    client = IMAPClient()
    conn = _RecordingConn()
    client._conn = conn
    result = client.search_emails(**kwargs)
    assert result == []
    return conn.search_criteria


def test_normal_inputs_preserved():
    criteria = _run_search(from_addr="shop@example.com", subject="Receipt")
    assert 'FROM "shop@example.com"' in criteria
    assert 'SUBJECT "Receipt"' in criteria


def test_quote_in_value_is_escaped():
    # A naive f-string would produce FROM "a" BODY "x", injecting a new term.
    criteria = _run_search(from_addr='a" BODY "x')
    assert 'FROM "a\\" BODY \\"x"' in criteria
    # The injected value stays inside one quoted string: only the delimiters
    # of FROM remain as bare quotes.
    assert criteria.count('"') == 2 + 2  # 2 escaped + 2 delimiters


def test_query_builds_escaped_or():
    criteria = _run_search(query='pay"load')
    assert 'OR SUBJECT "pay\\"load" BODY "pay\\"load"' in criteria


def test_no_criteria_is_all():
    criteria = _run_search()
    assert criteria == "(ALL)"


def test_dates_formatted():
    criteria = _run_search(since="2024-01-02", before="2024-03-04")
    assert "SINCE 02-Jan-2024" in criteria
    assert "BEFORE 04-Mar-2024" in criteria
