"""Receipt Sweep MCP Server.

Exposes IMAP email access as MCP tools so Claude can search inboxes,
read receipts, and extract spending data.
"""

import json
from pathlib import Path

try:
    from mcp.server.fastmcp import FastMCP
except (ImportError, ModuleNotFoundError):
    # mcp v2 renamed FastMCP to MCPServer
    from mcp.server.mcpserver import MCPServer as FastMCP

from mcp.types import ToolAnnotations

from .imap_client import ConnectionLost, IMAPClient
from .pdf_text import pdf_to_text
from .providers import list_providers

mcp = FastMCP(
    "receipt-sweep",
    instructions=(
        "Receipt Sweep connects to the user's email inbox via IMAP "
        "and provides tools to search for receipts, read email content, "
        "and read or download PDF attachments. Use these tools with the "
        "receipt-sweep skill to extract spending data and build spreadsheets. "
        "Mailbox access is serialized, so concurrent calls are safe but run one "
        "at a time; a dropped connection is re-established automatically."
    ),
)

# Single shared client instance per server process
_client = IMAPClient()


@mcp.tool(
    annotations=ToolAnnotations(
        title="List email providers", read_only_hint=True
    )
)
def list_email_providers() -> str:
    """List supported email providers and their setup instructions.

    Call this first to show the user which providers are supported
    and how to generate an App Password for their provider.
    """
    providers = list_providers()
    lines = ["Supported email providers:\n"]
    for p in providers:
        lines.append(f"**{p['name']}** (id: `{p['id']}`)")
        lines.append(f"  IMAP: {p['host']}:{p['port']}")
        lines.append(f"  Auth: {p['help']}")
        lines.append("")
    lines.append(
        "For other providers, pass the IMAP hostname directly to connect_email."
    )
    return "\n".join(lines)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Connect to email inbox",
        read_only_hint=False,
        destructive_hint=False,
    )
)
def connect_email(provider: str, email_address: str, app_password: str) -> str:
    """Connect to an email inbox via IMAP.

    Args:
        provider: Provider name ('gmail', 'yahoo', 'outlook', 'icloud')
                  or a raw IMAP hostname (e.g. 'imap.example.com').
        email_address: The full email address to sign into.
        app_password: An App Password for the account (NOT the regular password).
                      See list_email_providers() for how to create one.

    Returns a status message. The connection persists for subsequent tool calls.
    """
    if _client.connected:
        _client.disconnect()

    result = _client.connect(provider, email_address, app_password)
    if result["ok"]:
        return f"Connected to {result['email']} via {result['host']}."
    else:
        return f"Connection failed: {result['error']}"


@mcp.tool(
    annotations=ToolAnnotations(
        title="Disconnect email",
        read_only_hint=False,
        destructive_hint=False,
    )
)
def disconnect_email() -> str:
    """Disconnect from the current email inbox."""
    _client.disconnect()
    return "Disconnected."


@mcp.tool(
    annotations=ToolAnnotations(
        title="Check connection status", read_only_hint=True
    )
)
def connection_status() -> str:
    """Check whether an email connection is active."""
    if _client.connected:
        return f"Connected as {_client.email_address}."
    return "Not connected. Use connect_email() first."


@mcp.tool(
    annotations=ToolAnnotations(
        title="List mailbox folders", read_only_hint=True
    )
)
def list_folders() -> str:
    """List all folders/labels in the connected mailbox.

    Returns folder names that can be passed to search_emails and read_email.
    """
    if not _client.connected:
        return "Error: not connected. Call connect_email first."
    try:
        folders = _client.list_folders()
        return json.dumps(folders, indent=2)
    except Exception as e:
        return f"Error listing folders: {e}"


@mcp.tool(
    annotations=ToolAnnotations(
        title="Search emails in a folder", read_only_hint=True
    )
)
def search_emails(
    folder: str = "INBOX",
    from_address: str | None = None,
    subject_contains: str | None = None,
    body_or_subject: str | None = None,
    since_date: str | None = None,
    before_date: str | None = None,
    limit: int = 50,
) -> str:
    """Search for emails in a folder.

    Args:
        folder: Mailbox folder to search (default 'INBOX'). Use list_folders()
                to see all available folders. Common: INBOX, Sent, Trash,
                [Gmail]/All Mail, Bulk (Yahoo spam), Archive.
        from_address: Filter by sender email address.
        subject_contains: Filter by text in the subject line.
        body_or_subject: Search for text in the subject OR body.
        since_date: Only emails on or after this date (YYYY-MM-DD).
        before_date: Only emails before this date (YYYY-MM-DD).
        limit: Max results to return (default 50, newest first).

    Returns a JSON list of {id, date, from, subject} for matching emails.
    Use read_email() with the id to get the full content.
    """
    if not _client.connected:
        return "Error: not connected. Call connect_email first."
    try:
        results = _client.search_emails(
            folder=folder,
            query=body_or_subject,
            from_addr=from_address,
            subject=subject_contains,
            since=since_date,
            before=before_date,
            limit=limit,
        )
        if not results:
            return "No matching emails found."
        return json.dumps(results, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"Error searching: {e}"


@mcp.tool(
    annotations=ToolAnnotations(
        title="Read an email", read_only_hint=True
    )
)
def read_email(message_id: str, folder: str = "INBOX") -> str:
    """Read the full content of a specific email.

    Args:
        message_id: The message ID from search_emails results.
        folder: The folder the message is in (must match the search).

    Returns the email's date, sender, subject, body text, and a list of any
    attachments (with filenames and sizes). The body is taken from whichever
    of the plain-text or HTML parts contains the order details. If has_pdf is
    true and the body has no amount, call read_pdf_attachment.
    """
    if not _client.connected:
        return "Error: not connected. Call connect_email first."
    try:
        result = _client.read_email(message_id, folder=folder)
        if "error" in result:
            return f"Error: {result['error']}"
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"Error reading email: {e}"


@mcp.tool(
    annotations=ToolAnnotations(
        title="Read PDF attachment text", read_only_hint=True
    )
)
def read_pdf_attachment(message_id: str, filename: str, folder: str = "INBOX") -> str:
    """Extract the text of a PDF attachment, such as an emailed receipt.

    Use this when read_email lists a PDF attachment and the body only says
    something like "your receipt is attached".

    Args:
        message_id: The message ID from search_emails results.
        filename: The PDF's filename (from read_email's attachments list).
        folder: The folder the message is in.

    Returns the PDF's text, or an error message.
    """
    if not _client.connected:
        return "Error: not connected. Call connect_email first."
    try:
        data = _client.get_attachment(message_id, filename, folder=folder)
        if data is None:
            return f"Attachment '{filename}' not found in message {message_id}."
        return pdf_to_text(data)
    except Exception as e:
        return f"Error reading PDF attachment: {e}"


@mcp.tool(
    annotations=ToolAnnotations(
        title="Save email attachment",
        read_only_hint=False,
        destructive_hint=False,
    )
)
def save_attachment(
    message_id: str,
    filename: str,
    save_path: str,
    folder: str = "INBOX",
) -> str:
    """Download an email attachment and save it to disk.

    Args:
        message_id: The message ID from search_emails results.
        filename: The attachment filename (from read_email's attachments list).
        save_path: Local file path to save the attachment to.
        folder: The folder the message is in.

    Returns the path to the saved file, or an error message.
    """
    if not _client.connected:
        return "Error: not connected. Call connect_email first."
    try:
        data = _client.get_attachment(message_id, filename, folder=folder)
        if data is None:
            return f"Attachment '{filename}' not found in message {message_id}."
        out = Path(save_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        return f"Saved {len(data)} bytes to {save_path}"
    except Exception as e:
        return f"Error saving attachment: {e}"


@mcp.tool(
    annotations=ToolAnnotations(
        title="Search all folders", read_only_hint=True
    )
)
def search_all_folders(
    from_address: str | None = None,
    subject_contains: str | None = None,
    body_or_subject: str | None = None,
    since_date: str | None = None,
    before_date: str | None = None,
    limit_per_folder: int = 30,
) -> str:
    """Search across ALL folders in the mailbox (inbox, spam, trash, archive, custom folders).

    Same parameters as search_emails but runs the search in every folder.
    Returns results grouped by folder, plus any folders that could not be
    searched. Slower but thorough.
    """
    if not _client.connected:
        return "Error: not connected. Call connect_email first."
    try:
        folders = _client.list_folders()
    except Exception as e:
        return f"Error listing folders: {e}"

    all_results: dict[str, list] = {}
    failed: dict[str, str] = {}
    for folder in folders:
        try:
            results = _client.search_emails(
                folder=folder,
                query=body_or_subject,
                from_addr=from_address,
                subject=subject_contains,
                since=since_date,
                before=before_date,
                limit=limit_per_folder,
            )
            if results:
                # Tag each result with its folder
                for r in results:
                    r["folder"] = folder
                all_results[folder] = results
        except ConnectionLost as e:
            return f"Error: {e}"
        except Exception as e:
            # Report it rather than silently treating the folder as empty.
            failed[folder] = str(e)

    if not all_results and not failed:
        return "No matching emails found in any folder."

    total = sum(len(v) for v in all_results.values())
    output: dict = {"total_results": total, "by_folder": all_results}
    if failed:
        output["folders_not_searched"] = failed
    return json.dumps(output, indent=2, ensure_ascii=False)


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
