"""Tests for read_email body selection, using a fake IMAP connection."""

from receipt_sweep.imap_client import IMAPClient

PLAIN_EMAIL = (
    b"From: shop@example.com\r\n"
    b"To: me@example.com\r\n"
    b"Subject: Your receipt\r\n"
    b"Date: Wed, 02 Jan 2024 10:00:00 +0000\r\n"
    b'Content-Type: text/plain; charset="utf-8"\r\n'
    b"\r\n"
    b"Thank you for your order. Total: $12.34\r\n"
)

HTML_EMAIL = (
    b"From: shop@example.com\r\n"
    b"To: me@example.com\r\n"
    b"Subject: Your receipt\r\n"
    b"Date: Wed, 02 Jan 2024 10:00:00 +0000\r\n"
    b'Content-Type: text/html; charset="utf-8"\r\n'
    b"\r\n"
    b"<html><head><style>p{color:red}</style></head>"
    b"<body><p>Thank you for your order.</p><p>Total: $12.34</p></body></html>\r\n"
)


class _FetchConn:
    """Fake connection returning fixed RFC822 bytes from fetch()."""

    def __init__(self, raw):
        self._raw = raw

    def select(self, mailbox, readonly=True):
        return ("OK", [b"1"])

    def fetch(self, msg_id, spec):
        return ("OK", [(b"1 (RFC822 {%d}" % len(self._raw), self._raw)])


def _read(raw):
    client = IMAPClient()
    client._conn = _FetchConn(raw)
    return client.read_email("1")


def test_plain_text_only_returns_plain_body():
    result = _read(PLAIN_EMAIL)
    assert result["subject"] == "Your receipt"
    assert result["from"] == "shop@example.com"
    assert "Thank you for your order. Total: $12.34" in result["body"]
    # No HTML leaked in.
    assert "<" not in result["body"]


def test_html_only_returns_converted_text():
    result = _read(HTML_EMAIL)
    assert "Thank you for your order." in result["body"]
    assert "Total: $12.34" in result["body"]
    # Tags stripped and <style> contents removed.
    assert "<p>" not in result["body"]
    assert "color:red" not in result["body"]


def test_missing_message_returns_error():
    class _EmptyConn:
        def select(self, mailbox, readonly=True):
            return ("OK", [b"1"])

        def fetch(self, msg_id, spec):
            return ("OK", [None])

    client = IMAPClient()
    client._conn = _EmptyConn()
    result = client.read_email("99")
    assert "error" in result
