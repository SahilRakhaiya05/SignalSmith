from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.config import get_settings
from app.services.mcp_client import SplunkMCPClient

logger = logging.getLogger(__name__)


def _rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        results = data.get("results") or data.get("rows") or []
        if isinstance(results, list):
            return [r for r in results if isinstance(r, dict)]
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    return []


def _count_field(row: dict[str, Any]) -> int:
    for key in ("count", "Count", "event_count", "total"):
        if key in row and row[key] not in (None, ""):
            try:
                return int(float(row[key]))
            except (TypeError, ValueError):
                pass
    return 0


class SplunkAnalyticsService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.mcp = SplunkMCPClient()

    async def _query(self, spl: str, count: int = 50) -> tuple[list[dict[str, Any]], str]:
        await self.mcp.initialize()
        data, source = await self.mcp.run_splunk_query(spl, count=count)
        return _rows(data), source

    async def live_dashboard_data(self) -> dict[str, Any]:
        baseline = self.settings.splunk_baseline_index
        candidate = self.settings.splunk_candidate_index
        await self.mcp.initialize()

        panels: dict[str, Any] = {}
        queries = {
            "index_comparison": (
                f"search index={baseline} OR index={candidate} "
                f"| stats count as count by index | sort -count"
            ),
            "events_by_service": (
                f"search index={baseline} "
                f"| stats count as count by service | sort -count | head 12"
            ),
            "events_by_scenario": (
                f"search index={baseline} "
                f"| stats count as count by scenario | sort -count | head 10"
            ),
            "events_by_level": (
                f"search index={baseline} "
                f"| stats count as count by level | sort -count"
            ),
            "candidate_by_service": (
                f"search index={candidate} "
                f"| stats count as count by service | sort -count | head 12"
            ),
            "reducible_health_checks": (
                f"search index={baseline} event_type=health_check "
                f"| stats count as count by service | sort -count | head 8"
            ),
        }

        async def _panel(key: str, spl: str) -> tuple[str, dict[str, Any], str | None]:
            try:
                rows, row_source = await self._query(spl)
                return key, {"spl": spl, "rows": rows, "source": row_source}, row_source
            except Exception as exc:
                logger.warning("Analytics panel %s failed: %s", key, exc)
                return key, {"spl": spl, "rows": [], "error": str(exc)}, None

        results = await asyncio.gather(*[_panel(key, spl) for key, spl in queries.items()])
        source = self.mcp.mode
        for key, panel, row_source in results:
            panels[key] = panel
            if row_source:
                source = row_source

        index_chart = [
            {"name": r.get("index", "unknown"), "value": _count_field(r)}
            for r in panels.get("index_comparison", {}).get("rows", [])
        ]
        service_chart = [
            {"service": r.get("service", "unknown"), "count": _count_field(r)}
            for r in panels.get("events_by_service", {}).get("rows", [])
        ]
        scenario_chart = [
            {"scenario": r.get("scenario", "unknown"), "count": _count_field(r)}
            for r in panels.get("events_by_scenario", {}).get("rows", [])
        ]
        level_chart = [
            {"level": r.get("level", "unknown"), "count": _count_field(r)}
            for r in panels.get("events_by_level", {}).get("rows", [])
        ]
        health_chart = [
            {"service": r.get("service", "unknown"), "count": _count_field(r)}
            for r in panels.get("reducible_health_checks", {}).get("rows", [])
        ]

        service_compare: dict[str, dict[str, int]] = {}
        for r in panels.get("events_by_service", {}).get("rows", []):
            svc = str(r.get("service", "unknown"))
            service_compare[svc] = {"baseline": _count_field(r), "candidate": 0}
        for r in panels.get("candidate_by_service", {}).get("rows", []):
            svc = str(r.get("service", "unknown"))
            if svc not in service_compare:
                service_compare[svc] = {"baseline": 0, "candidate": 0}
            service_compare[svc]["candidate"] = _count_field(r)
        service_comparison_chart = [
            {"service": svc, **counts}
            for svc, counts in sorted(
                service_compare.items(),
                key=lambda x: x[1]["baseline"] + x[1]["candidate"],
                reverse=True,
            )[:10]
        ]

        baseline_total = next(
            (p["value"] for p in index_chart if baseline in p["name"]),
            0,
        )
        candidate_total = next(
            (p["value"] for p in index_chart if candidate in p["name"]),
            0,
        )
        reduction_pct = 0.0
        if baseline_total > 0 and candidate_total >= 0:
            reduction_pct = round((1 - candidate_total / baseline_total) * 100, 2)

        return {
            "source": source,
            "mcp_mode": self.mcp.mode,
            "official_mcp": self.mcp.is_mcp,
            "baseline_index": baseline,
            "candidate_index": candidate,
            "baseline_events": baseline_total,
            "candidate_events": candidate_total,
            "reduction_percent": reduction_pct if candidate_total > 0 else None,
            "charts": {
                "index_comparison": index_chart,
                "events_by_service": service_chart,
                "events_by_scenario": scenario_chart,
                "events_by_level": level_chart,
                "health_check_noise": health_chart,
                "service_comparison": service_comparison_chart,
            },
            "query_source": source,
            "panels": panels,
        }