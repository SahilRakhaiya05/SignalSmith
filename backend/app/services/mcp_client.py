from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

OFFICIAL_TOOLS = (
    "generate_spl",
    "run_splunk_query",
    "get_splunk_info",
    "get_indexes",
    "get_index_info",
    "get_saved_searches",
)

# Splunk MCP Server 1.x exposes splunk_* tool names; legacy clients use the names below.
LEGACY_TOOL_ALIASES: dict[str, str] = {
    "get_splunk_info": "splunk_get_info",
    "get_indexes": "splunk_get_indexes",
    "get_index_info": "splunk_get_index_info",
    "run_splunk_query": "splunk_run_query",
    "get_saved_searches": "splunk_get_knowledge_objects",
}


@dataclass
class MCPCallRecord:
    tool: str
    arguments: dict[str, Any]
    source: str
    success: bool
    summary: str
    duration_ms: float = 0.0


@dataclass
class SplunkMCPClient:
    """JSON-RPC 2.0 client for the official Splunk MCP Server (/services/mcp)."""

    mode: str = "offline"
    server_name: str | None = None
    server_version: str | None = None
    protocol_version: str | None = None
    tools: list[dict[str, Any]] = field(default_factory=list)
    call_history: list[MCPCallRecord] = field(default_factory=list)
    last_error: str | None = None
    status_note: str | None = None

    def __post_init__(self) -> None:
        self.settings = get_settings()
        self._available = False
        self._request_id = 0
        self._initialized = False

    @property
    def endpoint(self) -> str:
        return self.settings.splunk_mcp_endpoint

    @property
    def is_mcp(self) -> bool:
        return self.mode == "splunk_mcp" and self._available

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _auth_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.settings.splunk_mcp_token:
            headers["Authorization"] = f"Bearer {self.settings.splunk_mcp_token}"
        return headers

    def _auth(self) -> tuple[str, str] | None:
        if self.settings.splunk_mcp_token:
            return None
        from app.services.splunk_credentials import get_splunk_auth

        return get_splunk_auth()

    async def _rpc(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        async with httpx.AsyncClient(verify=False, timeout=60.0) as client:
            response = await client.post(
                self.endpoint,
                json=payload,
                headers=self._auth_headers(),
                auth=self._auth(),
            )
            if response.status_code == 404:
                try:
                    data = response.json()
                    if "error" in data:
                        err = data["error"]
                        raise RuntimeError(
                            f"MCP error {err.get('code')}: {err.get('message')}"
                        )
                except (json.JSONDecodeError, ValueError):
                    pass
                raise ConnectionError("mcp_not_installed")
            if response.status_code >= 400:
                raise ConnectionError(f"MCP HTTP {response.status_code}: {response.text[:300]}")

            content_type = response.headers.get("content-type", "")
            if "json" not in content_type:
                raise ConnectionError(f"MCP returned non-JSON: {response.text[:200]}")

            data = response.json()
            if "error" in data:
                err = data["error"]
                raise RuntimeError(f"MCP error {err.get('code')}: {err.get('message')}")
            return data.get("result", {})

    async def initialize(self) -> str:
        try:
            result = await self._rpc(
                "initialize",
                {"client": "SignalSmith AI", "version": "2.1.0"},
            )
            self._initialized = True
            server_info = result.get("serverInfo", {})
            self.server_name = server_info.get("name")
            self.server_version = server_info.get("version")
            self.protocol_version = result.get("protocolVersion")
            self._available = True
            self.mode = "splunk_mcp"
            self.last_error = None
            self.status_note = None

            try:
                await self._rpc("notifications/initialized", {})
            except Exception:
                pass

            await self.refresh_tools()
            return self.mode
        except Exception as exc:
            self._available = False
            self.mode = await self._detect_bridge_mode()
            if self.mode == "splunk_api":
                self.last_error = None
                self.status_note = (
                    "Official Splunk MCP Server is not installed. "
                    "All tools are running through the Splunk API and are fully operational."
                )
                self.tools = [{"name": t, "description": f"Splunk API: {t}"} for t in OFFICIAL_TOOLS]
                logger.info("MCP not installed; Splunk API fallback active")
            else:
                self.last_error = None if str(exc) == "mcp_not_installed" else str(exc)
                self.status_note = None
                logger.warning("MCP unavailable (%s), mode=%s", exc, self.mode)
            return self.mode

    async def _detect_bridge_mode(self) -> str:
        from app.services.mcp_rest_bridge import MCPRestBridge

        try:
            bridge = MCPRestBridge()
            info, source = await bridge.call_tool("get_splunk_info", {})
            if source == "splunk_api" and info.get("version"):
                return "splunk_api"
        except Exception:
            pass
        return "offline"

    async def refresh_tools(self) -> list[dict[str, Any]]:
        if not self.is_mcp:
            if self.mode == "splunk_api":
                self.tools = [{"name": t, "description": f"Splunk API: {t}"} for t in OFFICIAL_TOOLS]
                return self.tools
            self.tools = []
            return []
        try:
            result = await self._rpc("tools/list", {})
            self.tools = result.get("tools", [])
        except Exception as exc:
            self.last_error = str(exc)
            self.tools = [{"name": t} for t in OFFICIAL_TOOLS]
        return self.tools

    def _parse_tool_content(self, result: dict[str, Any]) -> Any:
        structured = result.get("structuredContent")
        if isinstance(structured, dict):
            return structured
        content = result.get("content", [])
        if not content:
            return result
        texts = [item.get("text", "") for item in content if item.get("type") == "text"]
        combined = "\n".join(texts).strip()
        if not combined:
            return result
        try:
            return json.loads(combined)
        except json.JSONDecodeError:
            return combined

    def _available_tool_names(self) -> set[str]:
        names: set[str] = set()
        for tool in self.tools:
            if isinstance(tool, dict) and tool.get("name"):
                names.add(str(tool["name"]))
            elif isinstance(tool, str):
                names.add(tool)
        return names

    def _resolve_tool_name(self, name: str) -> str | None:
        available = self._available_tool_names()
        if name in available:
            return name
        alias = LEGACY_TOOL_ALIASES.get(name)
        if alias and alias in available:
            return alias
        prefixed = f"splunk_{name.removeprefix('splunk_')}"
        if prefixed in available:
            return prefixed
        return None

    def _map_tool_arguments(
        self,
        logical_name: str,
        resolved_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        args = dict(arguments)
        if resolved_name == "splunk_get_index_info":
            if "index_name" not in args and "index" in args:
                args["index_name"] = args.pop("index")
            if "index_name" not in args and "name" in args:
                args["index_name"] = args.pop("name")
        if resolved_name == "splunk_get_knowledge_objects" and logical_name == "get_saved_searches":
            args.setdefault("type", "saved_searches")
        if resolved_name == "splunk_run_query":
            if "row_limit" not in args and "count" in args:
                args["row_limit"] = args.pop("count")
            if "earliest_time" not in args and "earliest" in args:
                args["earliest_time"] = args.pop("earliest")
            if "latest_time" not in args and "latest" in args:
                args["latest_time"] = args.pop("latest")
        if resolved_name == "splunk_get_indexes" and "row_limit" not in args:
            if "count" in args:
                args["row_limit"] = args.pop("count")
        return args

    async def _bridge_call(self, name: str, args: dict[str, Any]) -> tuple[Any, str]:
        from app.services.mcp_rest_bridge import MCPRestBridge

        bridge = MCPRestBridge()
        return await bridge.call_tool(name, args)

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> tuple[Any, str]:
        import time

        args = arguments or {}
        started = time.perf_counter()

        if not self.is_mcp:
            data, source = await self._bridge_call(name, args)
            elapsed = (time.perf_counter() - started) * 1000
            self._record_call(name, args, source, True, str(data)[:200], elapsed)
            return data, source

        resolved = self._resolve_tool_name(name)
        if not resolved:
            logger.info("MCP tool %s unavailable on server; using Splunk API bridge", name)
            data, source = await self._bridge_call(name, args)
            elapsed = (time.perf_counter() - started) * 1000
            self._record_call(name, args, source, True, str(data)[:200], elapsed)
            return data, source

        mapped_args = self._map_tool_arguments(name, resolved, args)
        try:
            result = await self._rpc("tools/call", {"name": resolved, "arguments": mapped_args})
            parsed = self._parse_tool_content(result)
            elapsed = (time.perf_counter() - started) * 1000
            self._record_call(name, args, "mcp", True, str(parsed)[:200], elapsed)
            return parsed, "mcp"
        except Exception as exc:
            logger.info("MCP tool %s failed (%s); using Splunk API bridge", name, exc)
            try:
                data, source = await self._bridge_call(name, args)
                elapsed = (time.perf_counter() - started) * 1000
                self._record_call(name, args, source, True, str(data)[:200], elapsed)
                return data, source
            except Exception as bridge_exc:
                elapsed = (time.perf_counter() - started) * 1000
                self._record_call(name, args, "mcp", False, str(bridge_exc), elapsed)
                raise bridge_exc from exc

    def _record_call(
        self,
        tool: str,
        arguments: dict[str, Any],
        source: str,
        success: bool,
        summary: str,
        duration_ms: float,
    ) -> None:
        self.call_history.append(
            MCPCallRecord(
                tool=tool,
                arguments=arguments,
                source=source,
                success=success,
                summary=summary,
                duration_ms=round(duration_ms, 2),
            )
        )
        if len(self.call_history) > 100:
            self.call_history = self.call_history[-100:]

    async def list_indexes(self) -> tuple[list[str], str]:
        data, source = await self.call_tool("get_indexes", {})
        if isinstance(data, dict):
            indexes = data.get("indexes") or data.get("index") or data.get("results") or []
            if isinstance(indexes, list):
                names = []
                for item in indexes:
                    if isinstance(item, str):
                        names.append(item)
                    elif isinstance(item, dict):
                        names.append(item.get("name") or item.get("title") or "")
                return [n for n in names if n], source
        if isinstance(data, list):
            return [str(x) for x in data], source
        return [], source

    async def list_saved_searches(self) -> tuple[list[dict[str, Any]], str]:
        data, source = await self.call_tool("get_saved_searches", {})
        if isinstance(data, dict):
            searches = (
                data.get("saved_searches")
                or data.get("searches")
                or data.get("results")
                or []
            )
            return searches if isinstance(searches, list) else [], source
        if isinstance(data, list):
            return data, source
        return [], source

    async def run_splunk_query(
        self,
        query: str,
        earliest: str = "-24h",
        latest: str = "now",
        count: int | None = None,
    ) -> tuple[Any, str]:
        args: dict[str, Any] = {"query": query}
        if earliest:
            args["earliest_time"] = earliest
        if latest:
            args["latest_time"] = latest
        if count is not None:
            args["count"] = count
        return await self.call_tool("run_splunk_query", args)

    async def generate_spl(self, natural_language: str) -> tuple[str, str]:
        if self.is_mcp and self._resolve_tool_name("generate_spl"):
            try:
                data, source = await self.call_tool("generate_spl", {"query": natural_language})
                if isinstance(data, dict):
                    return (
                        data.get("spl") or data.get("query") or data.get("search") or str(data),
                        source,
                    )
                return str(data), source
            except Exception as exc:
                logger.info("MCP generate_spl unavailable (%s), trying Gemini/templates", exc)

        from app.services.gemini_service import GeminiService

        gemini = GeminiService()
        if gemini.is_configured() and gemini.settings.gemini_enabled:
            try:
                spl = await gemini.generate_spl(natural_language)
                return spl, "gemini"
            except Exception as exc:
                logger.info("Gemini SPL generation unavailable (%s), using templates", exc)

        data, source = await self._bridge_call("generate_spl", {"query": natural_language})
        if isinstance(data, dict):
            return data.get("spl") or data.get("query") or data.get("search") or str(data), source
        return str(data), source

    async def get_splunk_info(self) -> tuple[dict[str, Any], str]:
        data, source = await self.call_tool("get_splunk_info", {})
        return data if isinstance(data, dict) else {"info": data}, source

    async def get_index_info(self, index: str) -> tuple[dict[str, Any], str]:
        data, source = await self.call_tool("get_index_info", {"index": index})
        return data if isinstance(data, dict) else {"index": index, "info": data}, source

    async def run_search_count(self, spl: str) -> tuple[int, str]:
        from app.services.splunk_data_service import _extract_count, spl_for_count

        data, source = await self.run_splunk_query(spl_for_count(spl))
        return _extract_count(data), source

    def status_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "available": self.is_mcp,
            "endpoint": self.endpoint,
            "server_name": self.server_name or ("Splunk API" if self.mode == "splunk_api" else None),
            "server_version": self.server_version,
            "protocol_version": self.protocol_version,
            "tools": [t.get("name", t) if isinstance(t, dict) else t for t in self.tools],
            "official_tools": list(OFFICIAL_TOOLS),
            "last_error": self.last_error,
            "status_note": self.status_note,
            "uses_splunk_api": self.mode == "splunk_api" and not self.is_mcp,
            "recent_calls": [
                {
                    "tool": c.tool,
                    "source": c.source,
                    "success": c.success,
                    "summary": c.summary,
                    "duration_ms": c.duration_ms,
                }
                for c in self.call_history[-10:]
            ],
        }