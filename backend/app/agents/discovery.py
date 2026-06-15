from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.models.analysis import AgentAction
from app.services.audit_log import AuditLogService
from app.services.mcp_client import SplunkMCPClient
from app.services.saved_searches import saved_search_catalog
from app.services.splunk_client import SplunkClient
from app.services.storage import Storage


class DiscoveryAgent:
    def __init__(
        self,
        storage: Storage,
        audit: AuditLogService,
        splunk: SplunkClient,
        mcp: SplunkMCPClient,
    ) -> None:
        self.storage = storage
        self.audit = audit
        self.splunk = splunk
        self.mcp = mcp

    async def discover(self, analysis_id: str) -> tuple[dict[str, Any], list[AgentAction], str]:
        timeline: list[AgentAction] = []
        mcp_mode = await self.mcp.initialize()
        connected, splunk_source = await self.splunk.connect()
        if mcp_mode == "splunk_mcp":
            mode = "splunk_mcp"
        elif connected:
            mode = "splunk_api"
        else:
            mode = "offline"

        timeline.append(
            AgentAction(
                timestamp=datetime.now(timezone.utc).isoformat(),
                agent="DiscoveryAgent",
                action="connect_splunk",
                source=splunk_source,
                detail=f"Splunk connection {'established' if connected else 'unavailable'}",
            )
        )
        self.audit.record(
            actor="DiscoveryAgent",
            action="connect_splunk",
            source=splunk_source,
            output_summary=f"connected={connected}",
            analysis_id=analysis_id,
        )

        indexes: list[str] = []
        index_source = splunk_source
        if mode in {"splunk_mcp", "splunk_api"}:
            mcp_indexes, index_source = await self.mcp.list_indexes()
            indexes = mcp_indexes
            timeline.append(
                AgentAction(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    agent="DiscoveryAgent",
                    action="discover_indexes",
                    source=index_source,
                    detail=f"Discovered {len(indexes)} indexes via {index_source}",
                )
            )
        if not indexes:
            indexes, index_source = await self.splunk.get_indexes()
            timeline.append(
                AgentAction(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    agent="DiscoveryAgent",
                    action="discover_indexes",
                    source=index_source,
                    detail=f"Discovered indexes: {', '.join(indexes)}",
                )
            )
        self.audit.record(
            actor="DiscoveryAgent",
            action="discover_indexes",
            source=index_source,
            output_summary=", ".join(indexes),
            analysis_id=analysis_id,
        )

        saved_searches: list[dict[str, Any]] = []
        search_source = "local"
        if mode in {"splunk_mcp", "splunk_api"}:
            mcp_searches, search_source = await self.mcp.list_saved_searches()
            saved_searches = mcp_searches
        if not saved_searches:
            saved_searches, search_source = self.splunk.get_saved_searches()
        if not saved_searches:
            saved_searches = saved_search_catalog()
            search_source = "local"

        timeline.append(
            AgentAction(
                timestamp=datetime.now(timezone.utc).isoformat(),
                agent="DiscoveryAgent",
                action="load_saved_searches",
                source=search_source,
                detail=f"Loaded {len(saved_searches)} saved searches",
            )
        )
        self.audit.record(
            actor="DiscoveryAgent",
            action="load_saved_searches",
            source=search_source,
            output_summary=f"count={len(saved_searches)}",
            analysis_id=analysis_id,
        )

        baseline_count, baseline_bytes = self.storage.event_file_stats("baseline_events.json")
        timeline.append(
            AgentAction(
                timestamp=datetime.now(timezone.utc).isoformat(),
                agent="DiscoveryAgent",
                action="summarize_events",
                source="local",
                detail=f"Baseline dataset: {baseline_count} events, {baseline_bytes} bytes",
            )
        )

        result = {
            "mode": mode,
            "indexes": indexes,
            "saved_searches": saved_searches,
            "baseline_event_count": baseline_count,
            "baseline_bytes": baseline_bytes,
        }
        return result, timeline, mode