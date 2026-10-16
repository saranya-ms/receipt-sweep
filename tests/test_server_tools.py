"""The MCP server registers every tool with directory-ready annotations."""

import asyncio

import pytest

pytest.importorskip("mcp")  # the server module needs the mcp SDK
from receipt_sweep import server  # noqa: E402

EXPECTED_TOOLS = {
    "list_email_providers",
    "connect_email",
    "disconnect_email",
    "connection_status",
    "list_folders",
    "search_emails",
    "read_email",
    "read_pdf_attachment",
    "save_attachment",
    "search_all_folders",
}


def _tools():
    return asyncio.run(server.mcp.list_tools())


def test_all_expected_tools_registered():
    names = {t.name for t in _tools()}
    assert names == EXPECTED_TOOLS


def test_status_reports_server_version_when_not_connected(monkeypatch):
    monkeypatch.setattr(server, "_client", server.IMAPClient())
    reply = server.connection_status()
    assert "Not connected" in reply
    assert f"server v{server.__version__}" in reply


def test_status_notices_a_dead_session(monkeypatch):
    def dead():
        raise server.ConnectionLost("The connection was lost. Call connect_email again.")

    client = server.IMAPClient()
    client._conn = object()
    monkeypatch.setattr(client, "ping", dead)
    monkeypatch.setattr(server, "_client", client)
    reply = server.connection_status()
    assert "connect_email again" in reply
    assert "Connected as" not in reply


def test_connect_reply_carries_server_version(monkeypatch):
    client = server.IMAPClient()
    monkeypatch.setattr(
        client, "connect",
        lambda *a, **k: {"ok": True, "email": "me@example.com", "host": "imap.example.com"},
    )
    monkeypatch.setattr(server, "_client", client)
    reply = server.connect_email("yahoo", "me@example.com", "app-password")
    assert reply.endswith(f"(receipt-sweep server v{server.__version__})")


def test_every_tool_has_title_and_a_hint():
    for t in _tools():
        ann = t.annotations
        assert ann is not None, f"{t.name} has no annotations"
        assert ann.title, f"{t.name} is missing a title"
        # The directory requires a readOnlyHint or destructiveHint on every tool.
        assert (
            ann.read_only_hint is not None or ann.destructive_hint is not None
        ), f"{t.name} is missing a read-only / destructive hint"
