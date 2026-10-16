"""Tests for extracting text from PDF receipts."""

import pytest

pytest.importorskip("pypdf")
from receipt_sweep.pdf_text import pdf_to_text  # noqa: E402


def _minimal_pdf(text: str) -> bytes:
    """Build a one-page PDF that draws `text` in Helvetica."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for i, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref,
    )
    return out


def test_extracts_receipt_total():
    text = pdf_to_text(_minimal_pdf("Invoice 160427 Total $41.03"))
    assert "Total $41.03" in text


def test_rejects_non_pdf_bytes():
    with pytest.raises(ValueError, match="not a PDF"):
        pdf_to_text(b"<html>not a pdf</html>")


def test_truncates_long_text():
    text = pdf_to_text(_minimal_pdf("x" * 200), max_chars=50)
    assert text.endswith("[... truncated ...]")
