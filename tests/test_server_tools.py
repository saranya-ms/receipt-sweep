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


def test_every_tool_has_title_and_a_hint():
    for t in _tools():
        ann = t.annotations
        assert ann is not None, f"{t.name} has no annotations"
        assert ann.title, f"{t.name} is missing a title"
        # The directory requires a readOnlyHint or destructiveHint on every tool.
        assert (
            ann.read_only_hint is not None or ann.destructive_hint is not None
        ), f"{t.name} is missing a read-only / destructive hint"
