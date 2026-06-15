from __future__ import annotations

import pytest

from app.services.mcp_client import LEGACY_TOOL_ALIASES, SplunkMCPClient
from app.services.mcp_rest_bridge import MCPRestBridge


@pytest.mark.asyncio
async def test_splunk_api_generate_spl():
    bridge = MCPRestBridge()
    result, source = await bridge.call_tool("generate_spl", {"query": "health check volume by service"})
    assert source == "splunk_api"
    assert "spl" in result
    assert "health_check" in result["spl"] or "health" in result["spl"].lower()


@pytest.mark.asyncio
async def test_splunk_api_get_indexes():
    bridge = MCPRestBridge()
    result, source = await bridge.call_tool("get_indexes", {})
    assert source in {"splunk_api", "local_catalog"}
    assert "indexes" in result


@pytest.mark.asyncio
async def test_mcp_client_offline_without_splunk(monkeypatch):
    from app.services.mcp_client import SplunkMCPClient

    client = SplunkMCPClient()

    async def fail_rpc(*_args, **_kwargs):
        raise ConnectionError("MCP unavailable")

    async def offline_bridge():
        return "offline"

    monkeypatch.setattr(client, "_rpc", fail_rpc)
    monkeypatch.setattr(client, "_detect_bridge_mode", offline_bridge)

    mode = await client.initialize()
    assert mode == "offline"
    assert not client.is_mcp


def test_resolve_tool_name_prefers_splunk_aliases():
    client = SplunkMCPClient()
    client.tools = [
        {"name": "splunk_run_query"},
        {"name": "splunk_get_indexes"},
        {"name": "generate_spl"},
    ]
    assert client._resolve_tool_name("run_splunk_query") == "splunk_run_query"
    assert client._resolve_tool_name("get_indexes") == "splunk_get_indexes"
    assert client._resolve_tool_name("generate_spl") == "generate_spl"
    assert client._resolve_tool_name("unknown_tool") is None


def test_map_tool_arguments_for_mcp_12():
    client = SplunkMCPClient()
    mapped = client._map_tool_arguments(
        "get_index_info",
        "splunk_get_index_info",
        {"index": "main"},
    )
    assert mapped["index_name"] == "main"
    assert "index" not in mapped

    mapped_query = client._map_tool_arguments(
        "run_splunk_query",
        "splunk_run_query",
        {"query": "index=main", "count": 10, "earliest": "-1h", "latest": "now"},
    )
    assert mapped_query["row_limit"] == 10
    assert mapped_query["earliest_time"] == "-1h"
    assert mapped_query["latest_time"] == "now"


def test_legacy_aliases_cover_official_tools():
    for legacy in ("get_indexes", "run_splunk_query", "get_splunk_info", "get_index_info", "get_saved_searches"):
        assert legacy in LEGACY_TOOL_ALIASES