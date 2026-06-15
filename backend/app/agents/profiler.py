from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from app.models.analysis import AgentAction
from app.models.events import TelemetryEvent
from app.services.saved_searches import SAVED_SEARCHES


class TelemetryProfiler:
    def profile(self, events: list[TelemetryEvent]) -> tuple[dict[str, Any], AgentAction]:
        total = len(events)
        by_service = Counter(e.service for e in events)
        by_event_type = Counter(e.event_type for e in events)
        by_level = Counter(e.level for e in events)
        by_scenario = Counter(e.scenario for e in events)

        pattern_key = lambda e: f"{e.service}|{e.event_type}|{e.level}|{e.scenario}"
        pattern_counts = Counter(pattern_key(e) for e in events)

        patterns = []
        for key, count in pattern_counts.most_common(50):
            service, event_type, level, scenario = key.split("|")
            matching = [e for e in events if pattern_key(e) == key]
            avg_size = sum(e.estimated_size_bytes for e in matching) / max(len(matching), 1)
            repetition_score = round(count / total, 4)
            patterns.append(
                {
                    "pattern": key,
                    "service": service,
                    "event_type": event_type,
                    "level": level,
                    "scenario": scenario,
                    "count": count,
                    "percent": round(100 * count / total, 2),
                    "avg_size_bytes": round(avg_size, 2),
                    "repetition_score": repetition_score,
                }
            )

        field_cardinality: dict[str, int] = {}
        for field in ("service", "event_type", "level", "scenario", "http_route", "country"):
            field_cardinality[field] = len({getattr(e, field) for e in events})

        search_fields: dict[str, list[str]] = {
            "payment_outage": ["service", "level", "http_status", "scenario"],
            "high_http_error_rate": ["http_status"],
            "slow_payment_requests": ["service", "duration_ms"],
            "credential_stuffing": ["scenario", "service", "event_type", "http_status"],
            "privileged_user_anomaly": ["is_privileged", "service", "event_type"],
        }

        reducible = sum(
            p["count"]
            for p in patterns
            if p["scenario"] in {"health_check", "debug_heartbeat"}
            or (p["level"] == "INFO" and p["scenario"] == "normal_traffic")
        )

        summary = {
            "total_events": total,
            "total_bytes": sum(e.estimated_size_bytes for e in events),
            "by_service": dict(by_service),
            "by_event_type": dict(by_event_type),
            "by_level": dict(by_level),
            "by_scenario": dict(by_scenario),
            "patterns": patterns,
            "field_cardinality": field_cardinality,
            "search_field_refs": search_fields,
            "reducible_estimate": reducible,
            "service_distribution": [
                {"service": k, "count": v, "percent": round(100 * v / total, 2)}
                for k, v in by_service.items()
            ],
            "category_distribution": [
                {"category": k, "count": v, "percent": round(100 * v / total, 2)}
                for k, v in by_scenario.items()
            ],
        }

        action = AgentAction(
            timestamp=datetime.now(timezone.utc).isoformat(),
            agent="TelemetryProfiler",
            action="profile_event_patterns",
            source="local",
            detail=f"Profiled {total} events into {len(patterns)} top patterns",
        )
        return summary, action