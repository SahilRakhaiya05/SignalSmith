from __future__ import annotations

import hashlib
from typing import Any

from app.agents.protection_map import ProtectionMapBuilder
from app.models.events import TelemetryEvent
from app.models.proposals import PolicyRecommendation, ProposalRecord


class PolicyEngine:
    def __init__(self, debug: bool = False) -> None:
        self.debug = debug
        self.protection = ProtectionMapBuilder()

    def apply(
        self,
        events: list[TelemetryEvent],
        proposal: ProposalRecord,
    ) -> tuple[list[TelemetryEvent], list[dict[str, Any]]]:
        """Apply recommendations to events. Never mutates baseline file."""
        audit: list[dict[str, Any]] = []
        surviving: list[TelemetryEvent] = []

        drop_recs = [r for r in proposal.recommendations if r.action == "drop"]
        sample_recs = [r for r in proposal.recommendations if r.action == "sample"]
        preserve_recs = [r for r in proposal.recommendations if r.action == "preserve"]

        for idx, event in enumerate(events):
            decision = self._decide(event, idx, drop_recs, sample_recs, preserve_recs)
            if decision["retain"]:
                surviving.append(event)
            if self.debug:
                audit.append(
                    {
                        "index": idx,
                        "trace_id": event.trace_id,
                        "retain": decision["retain"],
                        "reason": decision["reason"],
                        "rule_id": decision.get("rule_id"),
                    }
                )

        return surviving, audit

    def _decide(
        self,
        event: TelemetryEvent,
        index: int,
        drop_recs: list[PolicyRecommendation],
        sample_recs: list[PolicyRecommendation],
        preserve_recs: list[PolicyRecommendation],
    ) -> dict[str, Any]:
        protected, protect_reason = self.protection.is_protected(event)
        if protected:
            return {"retain": True, "reason": protect_reason or "protected", "rule_id": "protection_map"}

        for rec in preserve_recs:
            if self._matches_recommendation(event, rec):
                return {"retain": True, "reason": rec.reasoning, "rule_id": rec.id}

        for rec in drop_recs:
            if self._matches_recommendation(event, rec):
                return {"retain": False, "reason": f"Dropped by {rec.id}", "rule_id": rec.id}

        for rec in sample_recs:
            if self._matches_recommendation(event, rec):
                rate = float(rec.parameters.get("sample_rate", 0.5))
                if self._sample_keep(event, index, rate):
                    return {"retain": True, "reason": f"Sampled in by {rec.id}", "rule_id": rec.id}
                return {"retain": False, "reason": f"Sampled out by {rec.id}", "rule_id": rec.id}

        return {"retain": True, "reason": "default retain", "rule_id": None}

    def _matches_recommendation(self, event: TelemetryEvent, rec: PolicyRecommendation) -> bool:
        if rec.id == "rec_drop_health_checks":
            return event.event_type == "health_check"
        if rec.id == "rec_drop_debug_heartbeats":
            return event.event_type == "debug_heartbeat"
        if rec.id == "rec_sample_normal_traffic":
            return (
                event.scenario == "normal_traffic"
                and event.level == "INFO"
                and (event.http_status or 0) < 400
            )
        if rec.id == "rec_preserve_errors":
            return event.level in {"ERROR", "CRITICAL"} or (event.http_status or 0) >= 500
        if rec.id == "rec_preserve_security":
            return event.scenario == "credential_stuffing" or event.event_type == "failed_login"
        if rec.id == "rec_preserve_high_latency":
            return (event.duration_ms or 0) >= 1500
        if rec.id == "rec_preserve_privileged":
            return event.is_privileged
        if rec.id == "rec_preserve_rare_exceptions":
            return event.scenario == "rare_exception"
        return False

    def _sample_keep(self, event: TelemetryEvent, index: int, rate: float) -> bool:
        key = f"{event.trace_id}:{index}:{rate}"
        digest = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)
        return (digest % 10000) / 10000 < rate