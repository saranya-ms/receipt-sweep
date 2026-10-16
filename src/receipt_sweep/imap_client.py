"""IMAP client wrapper for receipt extraction."""

import email
import email.utils
import imaplib
import re
import ssl
from datetime import date, datetime
from email.header import decode_header
from html.parser import HTMLParser
from typing import Any

from .providers import get_provider


class _HTMLToText(HTMLParser):
    """Minimal HTML-to-text converter for email bodies."""

    def __init__(self):
        super().__init__()
        self._text: list[str] = []
        self._skip = False
        self._block_tags = {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6", "td", "th"}

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script"):
            self._skip = True
        if tag in self._block_tags:
            self._text.append("\n")

    def handle_endtag(self, tag):
        if tag in ("style", "script"):
            self._skip = False
        if tag in self._block_tags:
            self._text.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self._text.append(data)

    def get_text(self) -> str:
        raw = "".join(self._text)
        # Collapse whitespace but keep newlines
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in raw.splitlines()]
        # Remove consecutive blank lines
        result: list[str] = []
        prev_blank = False
        for line in lines:
            if not line:
                if not prev_blank:
                    result.append("")
                prev_blank = True
            else:
                result.append(line)
                prev_blank = False
        return "\n".join(result).strip()


def html_to_text(html: str) -> str:
    """Convert HTML to readable plain text."""
    parser = _HTMLToText()
    parser.feed(html)
    return parser.get_text()


def _imap_quote(value: str) -> str:
    """Return an IMAP quoted string, escaping backslashes and double quotes.

    Per RFC 3501, a quoted string is delimited by double quotes and the only
    characters that must be escaped inside it are ``\\`` and ``"``. Carriage
    returns and newlines are stripped so a crafted value cannot break out of
    the SEARCH command or inject extra criteria.
    """
    sanitized = value.replace("\r", " ").replace("\n", " ")
    escaped = sanitized.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _decode_header_value(raw: str | None) -> str:
    """Decode an RFC 2047 encoded header into a plain string."""
    if not raw:
        return ""
    parts = decode_header(raw)
    decoded: list[str] = []
    for data, charset in parts:
        if isinstance(data, bytes):
            decoded.append(data.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(data)
    return " ".join(decoded)


class IMAPClient:
    """Manages a single IMAP connection."""

    def __init__(self):
        self._conn: imaplib.IMAP4_SSL | None = None
        self._email: str = ""
        self._provider_id: str = ""

    @property
    def connected(self) -> bool:
        return self._conn is not None

    @property
    def email_address(self) -> str:
        return self._email

    def connect(self, provider_or_host: str, email_addr: str, password: str, port: int = 993) -> dict:
        """Connect and authenticate via IMAP.

        provider_or_host: a provider name ('gmail', 'yahoo', …) or a raw IMAP hostname.
        """
        provider = get_provider(provider_or_host)
        if provider:
            host = provider["host"]
            port = provider["port"]
            self._provider_id = provider_or_host.lower()
        else:
            host = provider_or_host
            self._provider_id = "custom"

        ctx = ssl.create_default_context()
        try:
            self._conn = imaplib.IMAP4_SSL(host, port, ssl_context=ctx)
            self._conn.login(email_addr, password)
        except imaplib.IMAP4.error as exc:
            self._conn = None
            return {"ok": False, "error": f"Login failed: {exc}"}
        except Exception as exc:
            self._conn = None
            return {"ok": False, "error": f"Connection failed: {exc}"}

        self._email = email_addr
        return {"ok": True, "email": email_addr, "host": host}

    def disconnect(self) -> dict:
        if self._conn:
            try:
                self._conn.logout()
            except Exception:
                pass
            self._conn = None
        self._email = ""
        return {"ok": True}

    def list_folders(self) -> list[str]:
        """Return all mailbox folder names."""
        if not self._conn:
            raise RuntimeError("Not connected")
        _status, data = self._conn.list()
        folders: list[str] = []
        for item in data:
            if isinstance(item, bytes):
                # Parse: (\\Flags) "/" "FolderName"
                match = re.search(rb'"([^"]*)"$|(\S+)$', item)
                if match:
                    # Python has no built-in modified-UTF-7 (IMAP) codec; decode
                    # as UTF-8 and fall back to ASCII for exotic folder names.
                    try:
                        name = (match.group(1) or match.group(2)).decode("utf-8")
                    except Exception:
                        name = (match.group(1) or match.group(2)).decode("ascii", errors="replace")
                    folders.append(name)
        return folders

    def search_emails(
        self,
        folder: str = "INBOX",
        query: str | None = None,
        from_addr: str | None = None,
        subject: str | None = None,
        since: str | None = None,
        before: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Search for emails. Returns list of {uid, date, from, subject, snippet}.

        since/before: YYYY-MM-DD strings.
        query: a text string to search in subject or body.
        """
        if not self._conn:
            raise RuntimeError("Not connected")

        try:
            status, _ = self._conn.select(f'"{folder}"', readonly=True)
            if status != "OK":
                # Try without quotes
                status, _ = self._conn.select(folder, readonly=True)
                if status != "OK":
                    return []
        except Exception:
            return []

        # Build IMAP search criteria
        criteria: list[str] = []
        if from_addr:
            criteria.append(f"FROM {_imap_quote(from_addr)}")
        if subject:
            criteria.append(f"SUBJECT {_imap_quote(subject)}")
        if since:
            try:
                d = datetime.strptime(since, "%Y-%m-%d")
                criteria.append(f'SINCE {d.strftime("%d-%b-%Y")}')
            except ValueError:
                pass
        if before:
            try:
                d = datetime.strptime(before, "%Y-%m-%d")
                criteria.append(f'BEFORE {d.strftime("%d-%b-%Y")}')
            except ValueError:
                pass
        if query:
            # Search in subject and body with OR
            quoted = _imap_quote(query)
            criteria.append(f"OR SUBJECT {quoted} BODY {quoted}")

        search_str = " ".join(criteria) if criteria else "ALL"

        try:
            status, data = self._conn.search(None, f"({search_str})")
        except imaplib.IMAP4.error:
            # Fallback: simpler search
            try:
                status, data = self._conn.search(None, "ALL")
            except Exception:
                return []

        if status != "OK" or not data[0]:
            return []

        msg_ids = data[0].split()
        # Take the most recent (last N)
        msg_ids = msg_ids[-limit:]
        msg_ids.reverse()  # newest first

        results: list[dict] = []
        for mid in msg_ids:
            try:
                _, msg_data = self._conn.fetch(mid, "(RFC822.HEADER)")
                if not msg_data or not msg_data[0]:
                    continue
                raw = msg_data[0][1] if isinstance(msg_data[0], tuple) else msg_data[0]
                msg = email.message_from_bytes(raw)

                date_str = msg.get("Date", "")
                parsed_date = email.utils.parsedate_to_datetime(date_str) if date_str else None

                results.append({
                    "id": mid.decode() if isinstance(mid, bytes) else str(mid),
                    "date": parsed_date.strftime("%Y-%m-%d %H:%M") if parsed_date else date_str,
                    "from": _decode_header_value(msg.get("From", "")),
                    "subject": _decode_header_value(msg.get("Subject", "")),
                })
            except Exception:
                continue

        return results

    def read_email(self, msg_id: str, folder: str = "INBOX", max_body_chars: int = 15000) -> dict:
        """Read the full content of an email by its ID.

        Returns {id, date, from, to, subject, body_text, body_html, attachments[]}.
        """
        if not self._conn:
            raise RuntimeError("Not connected")

        try:
            self._conn.select(f'"{folder}"', readonly=True)
        except Exception:
            self._conn.select(folder, readonly=True)

        _, msg_data = self._conn.fetch(msg_id.encode() if isinstance(msg_id, str) else msg_id, "(RFC822)")
        if not msg_data or not msg_data[0]:
            return {"error": f"Message {msg_id} not found"}

        raw = msg_data[0][1] if isinstance(msg_data[0], tuple) else msg_data[0]
        msg = email.message_from_bytes(raw)

        date_str = msg.get("Date", "")
        parsed_date = email.utils.parsedate_to_datetime(date_str) if date_str else None

        body_text = ""
        body_html = ""
        attachments: list[dict] = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                disposition = str(part.get("Content-Disposition", ""))

                if "attachment" in disposition:
                    filename = _decode_header_value(part.get_filename() or "")
                    attachments.append({
                        "filename": filename,
                        "content_type": content_type,
                        "size": len(part.get_payload(decode=True) or b""),
                    })
                elif content_type == "text/plain" and not body_text:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body_text = payload.decode(charset, errors="replace")
                elif content_type == "text/html" and not body_html:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body_html = payload.decode(charset, errors="replace")
        else:
            content_type = msg.get_content_type()
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                text = payload.decode(charset, errors="replace")
                if content_type == "text/html":
                    body_html = text
                else:
                    body_text = text

        # Prefer plain text; fall back to converted HTML
        display_body = body_text or (html_to_text(body_html) if body_html else "")
        if len(display_body) > max_body_chars:
            display_body = display_body[:max_body_chars] + "\n\n[... truncated ...]"

        return {
            "id": msg_id,
            "date": parsed_date.strftime("%Y-%m-%d %H:%M") if parsed_date else date_str,
            "from": _decode_header_value(msg.get("From", "")),
            "to": _decode_header_value(msg.get("To", "")),
            "subject": _decode_header_value(msg.get("Subject", "")),
            "body": display_body,
            "attachments": attachments,
            "has_pdf": any(a["content_type"] == "application/pdf" for a in attachments),
        }

    def get_attachment(self, msg_id: str, filename: str, folder: str = "INBOX") -> bytes | None:
        """Download a specific attachment by message ID and filename."""
        if not self._conn:
            raise RuntimeError("Not connected")

        try:
            self._conn.select(f'"{folder}"', readonly=True)
        except Exception:
            self._conn.select(folder, readonly=True)

        _, msg_data = self._conn.fetch(msg_id.encode() if isinstance(msg_id, str) else msg_id, "(RFC822)")
        if not msg_data or not msg_data[0]:
            return None

        raw = msg_data[0][1] if isinstance(msg_data[0], tuple) else msg_data[0]
        msg = email.message_from_bytes(raw)

        for part in msg.walk():
            if "attachment" in str(part.get("Content-Disposition", "")):
                part_filename = _decode_header_value(part.get_filename() or "")
                if part_filename == filename:
                    return part.get_payload(decode=True)
        return None
