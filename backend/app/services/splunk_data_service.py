from __future__ import annotations

import json
import logging
from typing import Any

from app.config import get_settings
from app.models.events import TelemetryEvent
from app.services.mcp_client import SplunkMCPClient
from app.services.splunk_client import SplunkClient
from app.services.splunk_credentials import get_splunk_auth

logger = logging.getLogger(__name__)


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).lower() in {"1", "true", "yes"}


def _parse_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _row_to_event(row: dict[str, Any]) -> TelemetryEvent | None:
    if "_raw" in row and len(row) <= 2:
        try:
            row = json.loads(row["_raw"])
        except (json.JSONDecodeError, TypeError):
            pass

    service = row.get("service") or row.get("Service") or "unknown"
    event_type = row.get("event_type") or row.get("EventType") or "unknown"
    if service == "unknown" and event_type == "unknown":
        return None

    payload = row.get("event") if isinstance(row.get("event"), dict) else row
    if isinstance(payload, dict) and payload.get("service"):
        row = payload

    return TelemetryEvent(
        timestamp=str(row.get("timestamp") or row.get("_time") or ""),
        service=str(row.get("service") or "unknown"),
        environment=str(row.get("environment") or "production"),
        level=str(row.get("level") or "INFO"),
        event_type=str(row.get("event_type") or "unknown"),
        message=str(row.get("message") or ""),
        trace_id=str(row.get("trace_id") or row.get("_cd") or row.get("_serial") or "unknown"),
        user_id=row.get("user_id"),
        http_method=row.get("http_method"),
        http_route=row.get("http_route"),
        http_status=_parse_int(row.get("http_status")) if row.get("http_status") is not None else None,
        duration_ms=_parse_int(row.get("duration_ms")) if row.get("duration_ms") is not None else None,
        source_ip=row.get("source_ip"),
        country=row.get("country"),
        is_privileged=_parse_bool(row.get("is_privileged")),
        scenario=str(row.get("scenario") or "unknown"),
        estimated_size_bytes=_parse_int(row.get("estimated_size_bytes"), 400),
    )


def spl_for_count(spl: str) -> str:
    """Wrap a filtering SPL query so Splunk returns a single aggregate count row."""
    normalized = spl.strip()
    lower = normalized.lower()
    if "| stats" in lower:
        return normalized
    return f"{normalized} | stats count as count"


def _extract_count(data: Any) -> int:
    if isinstance(data, int):
        return data

    def _from_row(row: dict[str, Any]) -> int | None:
        for key in ("count", "Count", "event_count", "total"):
            if key in row and row[key] not in (None, ""):
                return _parse_int(row[key])
        return None

    if isinstance(data, dict):
        results = data.get("results") or data.get("rows") or []
        if isinstance(results, list) and results:
            first = results[0]
            if isinstance(first, dict):
                parsed = _from_row(first)
                if parsed is not None:
                    return parsed
        if "count" in data and not isinstance(data.get("results"), list):
            return _parse_int(data["count"])
        total_rows = data.get("total_rows")
        if total_rows is not None and isinstance(results, list) and len(results) == 1:
            only = results[0] if results else None
            if isinstance(only, dict) and _from_row(only) is not None:
                return _parse_int(total_rows)

    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            parsed = _from_row(first)
            if parsed is not None:
                return parsed

    if isinstance(data, str):
        import re

        match = re.search(r'"count"\s*:\s*"?(\d+)"?', data)
        if match:
            return int(match.group(1))
    return 0


class SplunkDataService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.splunk = SplunkClient()
        self.mcp = SplunkMCPClient()

    async def connect(self) -> tuple[bool, str]:
        return await self.splunk.connect()

    async def index_event_count(self, index: str) -> tuple[int, str]:
        await self.mcp.initialize()
        spl = f"index={index} | stats count as count"
        data, source = await self.mcp.run_splunk_query(spl)
        return _extract_count(data), source

    async def profile_index(self, index: str) -> tuple[dict[str, Any], str]:
        await self.mcp.initialize()
        queries = {
            "by_service": f"index={index} | stats count as count by service | sort -count",
            "by_event_type": f"index={index} | stats count as count by event_type | sort -count",
            "by_scenario": f"index={index} | stats count as count by scenario | sort -count",
            "by_level": f"index={index} | stats count as count by level | sort -count",
            "total": f"index={index} | stats count as count",
        }
        source = "splunk_api"
        results: dict[str, Any] = {}
        for key, spl in queries.items():
            data, src = await self.mcp.run_splunk_query(spl)
            source = src
            rows = []
            if isinstance(data, dict):
                rows = data.get("results") or []
            elif isinstance(data, list):
                rows = data
            results[key] = rows

        total = _extract_count(results.get("total"))
        by_service = {
            str(r.get("service", "unknown")): _parse_int(r.get("count"))
            for r in results.get("by_service", [])
            if isinstance(r, dict)
        }
        by_event_type = {
            str(r.get("event_type", "unknown")): _parse_int(r.get("count"))
            for r in results.get("by_event_type", [])
            if isinstance(r, dict)
        }
        by_scenario = {
            str(r.get("scenario", "unknown")): _parse_int(r.get("count"))
            for r in results.get("by_scenario", [])
            if isinstance(r, dict)
        }
        by_level = {
            str(r.get("level", "unknown")): _parse_int(r.get("count"))
            for r in results.get("by_level", [])
            if isinstance(r, dict)
        }

        reducible = sum(
            by_scenario.get(s, 0)
            for s in ("health_check", "debug_heartbeat")
        ) + sum(
            c
            for scen, c in by_scenario.items()
            if scen == "normal_traffic"
        )

        profile = {
            "total_events": total,
            "total_bytes": total * 430,
            "by_service": by_service,
            "by_event_type": by_event_type,
            "by_scenario": by_scenario,
            "by_level": by_level,
            "patterns": [],
            "field_cardinality": {},
            "search_field_refs": {},
            "reducible_estimate": reducible,
            "service_distribution": [
                {"service": k, "count": v, "percent": round(100 * v / max(total, 1), 2)}
                for k, v in sorted(by_service.items(), key=lambda x: -x[1])
            ],
            "category_distribution": [
                {"category": k, "count": v, "percent": round(100 * v / max(total, 1), 2)}
                for k, v in sorted(by_scenario.items(), key=lambda x: -x[1])
            ],
            "source": "splunk_spl",
            "index": index,
        }
        return profile, source

    async def export_events(self, index: str, limit: int | None = None) -> tuple[list[TelemetryEvent], str]:
        limit = limit or self.settings.profile_export_limit
        await self.mcp.initialize()
        spl = (
            f"search index={index} earliest=-30d | head {limit} "
            "| fields timestamp service environment level event_type message trace_id "
            "user_id http_method http_route http_status duration_ms source_ip country "
            "is_privileged scenario estimated_size_bytes"
        )
        data, source = await self.mcp.call_tool(
            "run_splunk_query",
            {"query": spl, "count": limit},
        )
        rows: list[dict[str, Any]] = []
        if isinstance(data, dict):
            rows = data.get("results") or []
        elif isinstance(data, list):
            rows = data

        events: list[TelemetryEvent] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            event = _row_to_event(row)
            if event:
                events.append(event)

        if not events and self.splunk.connected:
            events = await self._export_via_rest(index, limit)
            source = "splunk_rest"

        return events, source

    async def _export_via_rest(self, index: str, limit: int) -> list[TelemetryEvent]:
        spl = (
            f"search index={index} earliest=-30d | head {limit} "
            "| table timestamp service environment level event_type message trace_id "
            "user_id http_method http_route http_status duration_ms source_ip country "
            "is_privileged scenario estimated_size_bytes"
        )
        try:
            async with __import__("httpx").AsyncClient(verify=False, timeout=180.0) as client:
                resp = await client.post(
                    f"{self.settings.splunk_api_base}/services/search/jobs/oneshot",
                    data={"search": spl, "output_mode": "json", "count": limit},
                    auth=get_splunk_auth(),
                )
                if resp.status_code != 200:
                    return []
                payload = resp.json()
                events = []
                for row in payload.get("results", []):
                    event = _row_to_event(row)
                    if event:
                        events.append(event)
                return events
        except Exception as exc:
            logger.warning("REST export failed: %s", exc)
            return []

    async def bootstrap_baseline(self) -> dict[str, Any]:
        index = self.settings.splunk_baseline_index
        connected, mode = await self.connect()
        if not connected:
            raise RuntimeError("Splunk is not reachable. Connect Splunk before bootstrapping.")

        await self.splunk.ensure_indexes()
        count, count_source = await self.index_event_count(index)
        if count == 0:
            raise RuntimeError(f"Index {index} has no events. Ingest telemetry first.")

        profile, profile_source = await self.profile_index(index)
        events, export_source = await self.export_events(index)

        return {
            "index": index,
            "splunk_mode": mode,
            "event_count": count,
            "count_source": count_source,
            "exported_events": len(events),
            "export_source": export_source,
            "profile": profile,
            "profile_source": profile_source,
            "events": events,
        }