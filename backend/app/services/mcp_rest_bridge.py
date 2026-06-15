from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.config import get_settings
from app.services.saved_searches import saved_search_catalog


class MCPRestBridge:
    """Splunk API implementations of MCP tools when the official MCP Server app is unavailable."""

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> tuple[Any, str]:
        handlers = {
            "get_indexes": self._get_indexes,
            "get_index_info": self._get_index_info,
            "get_saved_searches": self._get_saved_searches,
            "get_splunk_info": self._get_splunk_info,
            "run_splunk_query": self._run_splunk_query,
            "generate_spl": self._generate_spl,
        }
        handler = handlers.get(name)
        if not handler:
            raise ValueError(f"Unknown MCP tool: {name}")
        return await handler(arguments)

    def _auth(self) -> tuple[str, str]:
        settings = get_settings()
        from app.services.splunk_credentials import get_splunk_auth

        return get_splunk_auth()

    def _base(self) -> str:
        return get_settings().splunk_api_base

    async def _get_splunk_info(self, _args: dict[str, Any]) -> tuple[dict[str, Any], str]:
        async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
            resp = await client.get(
                f"{self._base()}/services/server/info",
                params={"output_mode": "json"},
                auth=self._auth(),
            )
            if resp.status_code != 200:
                return {"error": f"HTTP {resp.status_code}"}, "splunk_api"
            content = resp.json()["entry"][0]["content"]
            return {
                "version": content.get("version"),
                "build": content.get("build"),
                "serverName": content.get("serverName"),
                "os_name": content.get("os_name"),
                "source": "splunk_splunk_api",
            }, "splunk_api"

    async def _get_indexes(self, _args: dict[str, Any]) -> tuple[dict[str, Any], str]:
        async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
            resp = await client.get(
                f"{self._base()}/services/data/indexes",
                params={"output_mode": "json", "count": 0},
                auth=self._auth(),
            )
            if resp.status_code != 200:
                settings = get_settings()
                return {
                    "indexes": [settings.splunk_baseline_index, settings.splunk_candidate_index],
                }, "splunk_api"
            names = [e.get("name", "") for e in resp.json().get("entry", []) if e.get("name")]
            return {"indexes": names}, "splunk_api"

    async def _get_index_info(self, args: dict[str, Any]) -> tuple[dict[str, Any], str]:
        index = args.get("index") or args.get("name", "")
        async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
            resp = await client.get(
                f"{self._base()}/services/data/indexes/{index}",
                params={"output_mode": "json"},
                auth=self._auth(),
            )
            if resp.status_code != 200:
                return {"index": index, "exists": False}, "splunk_api"
            content = resp.json()["entry"][0]["content"]
            return {
                "index": index,
                "exists": True,
                "totalEventCount": content.get("totalEventCount"),
                "currentDBSizeMB": content.get("currentDBSizeMB"),
                "maxDataSizeMB": content.get("maxDataSizeMB"),
            }, "splunk_api"

    async def _get_saved_searches(self, _args: dict[str, Any]) -> tuple[dict[str, Any], str]:
        async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
            resp = await client.get(
                f"{self._base()}/servicesNS/-/-/saved/searches",
                params={"output_mode": "json", "count": 0},
                auth=self._auth(),
            )
            if resp.status_code == 200:
                searches = []
                for entry in resp.json().get("entry", []):
                    content = entry.get("content", {})
                    searches.append(
                        {
                            "name": entry.get("name"),
                            "search": content.get("search"),
                            "description": content.get("description", ""),
                        }
                    )
                if searches:
                    return {"saved_searches": searches}, "splunk_api"

        return {"saved_searches": saved_search_catalog()}, "local_catalog"

    async def _run_splunk_query(self, args: dict[str, Any]) -> tuple[dict[str, Any], str]:
        query = args.get("query") or args.get("spl") or args.get("search", "")
        search = query if query.strip().lower().startswith("search") else f"search {query}"
        async with httpx.AsyncClient(verify=False, timeout=120.0) as client:
            resp = await client.post(
                f"{self._base()}/services/search/jobs/oneshot",
                data={
                    "search": search,
                    "output_mode": "json",
                    "count": args.get("count", 25000),
                },
                auth=self._auth(),
            )
            if resp.status_code != 200:
                return {"error": f"HTTP {resp.status_code}", "query": search}, "splunk_api"

            try:
                payload = resp.json()
                results = payload.get("results", [])
                return {"results": results, "count": len(results), "query": search}, "splunk_api"
            except json.JSONDecodeError:
                match = re.search(r'"count"\s*:\s*"?(\d+)"?', resp.text)
                count = int(match.group(1)) if match else 0
                return {"count": count, "query": search, "raw": resp.text[:500]}, "splunk_api"

    async def _generate_spl(self, args: dict[str, Any]) -> tuple[dict[str, Any], str]:
        """Template-based SPL generation when Splunk hosted AI / MCP generate_spl is unavailable."""
        nl = (args.get("query") or args.get("natural_language") or "").lower().strip()
        settings = get_settings()
        baseline = settings.splunk_baseline_index
        candidate = settings.splunk_candidate_index

        templates: list[tuple[tuple[str, ...], str]] = [
            (
                ("health", "heartbeat", "probe"),
                f"search index={baseline} event_type=health_check | stats count by service | sort -count",
            ),
            (
                ("login", "auth", "failed", "privilege"),
                f"search index={baseline} service=auth (event_type=login_failure OR privileged=true) | stats count",
            ),
            (
                ("checkout", "payment", "error"),
                f"search index={baseline} (service=checkout OR service=payment) level=ERROR | stats count by service",
            ),
            (
                ("compare", "baseline", "candidate", "reduction"),
                f"search index={baseline} OR index={candidate} | stats count by index",
            ),
            (
                ("volume", "top", "service"),
                f"search index={baseline} | stats count by service | sort -count | head 10",
            ),
            (
                ("anomaly", "spike", "rare"),
                f"search index={baseline} | rare event_type | head 20",
            ),
        ]

        spl = f"search index={baseline} | head 100"
        for keywords, template in templates:
            if any(k in nl for k in keywords):
                spl = template
                break

        return {
            "spl": spl,
            "natural_language": args.get("query") or args.get("natural_language"),
            "note": "Generated via REST bridge templates. Install Splunk MCP Server for hosted AI generate_spl.",
            "source": "splunk_api_templates",
        }, "splunk_api"