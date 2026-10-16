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


def _multipart(text_part, html_part, extra_parts=b""):
    return (
        b"From: orders@store.example\r\n"
        b"Subject: Order Confirmation #1ABC\r\n"
        b"Date: Wed, 02 Jan 2024 10:00:00 +0000\r\n"
        b"MIME-Version: 1.0\r\n"
        b'Content-Type: multipart/mixed; boundary="BOUND"\r\n'
        b"\r\n"
        b"--BOUND\r\n"
        b'Content-Type: text/plain; charset="utf-8"\r\n\r\n'
        + text_part + b"\r\n"
        b"--BOUND\r\n"
        b'Content-Type: text/html; charset="utf-8"\r\n\r\n'
        + html_part + b"\r\n"
        + extra_parts
        + b"--BOUND--\r\n"
    )


def test_links_only_text_part_falls_back_to_html_totals():
    # Old Navy style: the plain-text part has only links; totals are in HTML.
    raw = _multipart(
        b"Old Navy\r\nhttps://click.example/abc\r\nUnsubscribe: https://click.example/u",
        b"<html><body><table><tr><td>Subtotal</td><td>$40.00</td></tr>"
        b"<tr><td>Tax</td><td>$6.00</td></tr>"
        b"<tr><td>Total</td><td>$46.00</td></tr></table></body></html>",
    )
    body = _read(raw)["body"]
    assert "$46.00" in body
    assert "<td>" not in body


def test_plain_text_kept_when_it_has_the_amounts():
    raw = _multipart(
        b"Order total: $12.34",
        b"<html><body><p>Order total: $12.34</p></body></html>",
    )
    assert _read(raw)["body"] == "Order total: $12.34"


def test_raw_html_in_text_part_is_converted():
    raw = _multipart(
        b"<table><tr><td>Total</td><td>$9.99</td></tr></table>",
        b"",
    )
    body = _read(raw)["body"]
    assert "$9.99" in body
    assert "<table>" not in body


PDF_PART_OCTET = (
    b"--BOUND\r\n"
    b"Content-Type: application/octet-stream\r\n"
    b'Content-Disposition: attachment; filename="receipt_160427.pdf"\r\n'
    b"Content-Transfer-Encoding: base64\r\n\r\n"
    b"JVBERi0xLjQK\r\n"
)

PDF_PART_INLINE = (
    b"--BOUND\r\n"
    b'Content-Type: application/pdf; name="invoice.pdf"\r\n'
    b"Content-Transfer-Encoding: base64\r\n\r\n"
    b"JVBERi0xLjQK\r\n"
)


def test_pdf_with_generic_mime_type_sets_has_pdf():
    # la Vie en Rose sends its PDF receipt as application/octet-stream.
    result = _read(_multipart(b"Your receipt is attached.", b"", PDF_PART_OCTET))
    assert result["has_pdf"] is True
    assert result["attachments"][0]["filename"] == "receipt_160427.pdf"


def test_inline_pdf_without_attachment_disposition_is_listed():
    result = _read(_multipart(b"Your receipt is attached.", b"", PDF_PART_INLINE))
    assert result["has_pdf"] is True
    assert [a["filename"] for a in result["attachments"]] == ["invoice.pdf"]
