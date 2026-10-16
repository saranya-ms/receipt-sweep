"""Extract readable text from PDF receipts attached to emails."""

import io


def pdf_to_text(data: bytes, max_chars: int = 15000) -> str:
    """Return the text of a PDF, or raise ValueError if it can't be read.

    Many stores (e.g. la Vie en Rose) email the receipt as a PDF and put no
    amount in the body; this lets Claude read the totals directly.
    """
    if not data.lstrip()[:5].startswith(b"%PDF"):
        raise ValueError("The attachment is not a PDF.")

    # Imported lazily so the server still starts if pypdf is missing.
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted and not reader.decrypt(""):
        raise ValueError("The PDF is password-protected.")

    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    text = "\n\n".join(p for p in pages if p)
    if not text:
        raise ValueError("The PDF has no extractable text (it may be a scanned image).")
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[... truncated ...]"
    return text
