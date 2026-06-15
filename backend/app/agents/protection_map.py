from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.models.analysis import AgentAction
from app.models.events import TelemetryEvent
from app.services.saved_searches import event_matches_search, get_active_saved_searches


class ProtectionMapBuilder:
    RULES = [
        ("error_critical", "Protect ERROR and CRITICAL severity events", lambda e: e.level in {"ERROR", "CRITICAL"}),
        ("http_5xx", "Protect HTTP 5xx responses", lambda e: (e.http_status or 0) >= 500),
        ("high_latency", "Protect requests with duration_ms >= 1500", lambda e: (e.duration_ms or 0) >= 1500),
        ("failed_auth", "Protect failed authentication events", lambda e: e.event_type == "failed_login"),
        ("credential_stuffing", "Protect credential stuffing events", lambda e: e.scenario == "credential_stuffing"),
        ("privileged_user", "Protect privileged-user events", lambda e: e.is_privileged),
        ("rare_exception", "Protect rare application exceptions", lambda e: e.scenario == "rare_exception"),
        ("payment_outage", "Protect payment outage incident events", lambda e: e.scenario == "payment_outage"),
        ("slow_checkout", "Protect slow checkout incident events", lambda e: e.scenario == "slow_checkout"),
    ]

    def build(self, events: list[TelemetryEvent]) -> tuple[list[dict[str, Any]], AgentAction]:
        protected_patterns: list[dict[str, Any]] = []

        for rule_id, reason, predicate in self.RULES:
            matched = [e for e in events if predicate(e)]
            if matched:
                protected_patterns.append(
                    {
                        "rule_id": rule_id,
                        "reason": reason,
                        "event_count": len(matched),
                        "percent": round(100 * len(matched) / len(events), 2),
                        "sample_event_types": list({e.event_type for e in matched[:5]}),
                    }
                )

        for search in get_active_saved_searches():
            matched = [e for e in events if event_matches_search(e, search)]
            if matched:
                protected_patterns.append(
                    {
                        "rule_id": f"saved_search_{search.id}",
                        "reason": f"Required by saved search: {search.name}",
                        "event_count": len(matched),
                        "percent": round(100 * len(matched) / len(events), 2),
                        "sample_event_types": list({e.event_type for e in matched[:5]}),
                        "saved_search_id": search.id,
                    }
                )
            elif search.source == "custom":
                protected_patterns.append(
                    {
                        "rule_id": f"saved_search_{search.id}",
                        "reason": f"Custom detection (SPL replay): {search.name}",
                        "event_count": 0,
                        "percent": 0.0,
                        "sample_event_types": [],
                        "saved_search_id": search.id,
                        "spl_only": True,
                    }
                )

        action = AgentAction(
            timestamp=datetime.now(timezone.utc).isoformat(),
            agent="ProtectionMapBuilder",
            action="build_protection_map",
            source="local",
            detail=f"Built protection map with {len(protected_patterns)} protected patterns",
        )
        return protected_patterns, action

    def is_protected(self, event: TelemetryEvent) -> tuple[bool, str | None]:
        for rule_id, reason, predicate in self.RULES:
            if predicate(event):
                return True, reason
        for search in get_active_saved_searches():
            if event_matches_search(event, search):
                return True, f"Required by saved search: {search.name}"
        return False, None