from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.models.analysis import AgentAction
from app.models.events import TelemetryEvent
from app.models.proposals import PolicyRecommendation, ProposalRecord


class PolicyGenerator:
    def generate(
        self,
        analysis_id: str,
        events: list[TelemetryEvent],
        profile: dict[str, Any],
    ) -> tuple[ProposalRecord, AgentAction]:
        total = len(events)
        recommendations: list[PolicyRecommendation] = []

        health_checks = [e for e in events if e.event_type == "health_check"]
        if health_checks:
            recommendations.append(
                PolicyRecommendation(
                    id="rec_drop_health_checks",
                    action="drop",
                    condition='event_type="health_check"',
                    affected_event_count=len(health_checks),
                    estimated_reduction=len(health_checks),
                    risk_level="low",
                    reasoning="Successful health checks are high-volume and low diagnostic value.",
                    spl_query='event_type="health_check" AND http_status=200',
                    affected_saved_searches=[],
                )
            )

        heartbeats = [e for e in events if e.event_type == "debug_heartbeat"]
        if heartbeats:
            recommendations.append(
                PolicyRecommendation(
                    id="rec_drop_debug_heartbeats",
                    action="drop",
                    condition='event_type="debug_heartbeat"',
                    affected_event_count=len(heartbeats),
                    estimated_reduction=len(heartbeats),
                    risk_level="low",
                    reasoning="Repetitive debug heartbeats add noise without operational signal.",
                    spl_query='event_type="debug_heartbeat"',
                    affected_saved_searches=[],
                )
            )

        normal_traffic = [
            e
            for e in events
            if e.scenario == "normal_traffic" and e.level == "INFO" and (e.http_status or 0) < 400
        ]
        if normal_traffic:
            sample_rate = 0.25
            estimated_reduction = int(len(normal_traffic) * (1 - sample_rate))
            recommendations.append(
                PolicyRecommendation(
                    id="rec_sample_normal_traffic",
                    action="sample",
                    condition='scenario="normal_traffic" AND level="INFO" AND http_status<400',
                    affected_event_count=len(normal_traffic),
                    estimated_reduction=estimated_reduction,
                    risk_level="medium",
                    reasoning="Probabilistic sampling of routine successful traffic reduces volume while preserving error signals.",
                    spl_query='scenario="normal_traffic" | sample 0.25',
                    affected_saved_searches=[],
                    parameters={"sample_rate": sample_rate},
                )
            )

        preserve_rules = [
            (
                "rec_preserve_errors",
                "preserve",
                'level IN ("ERROR","CRITICAL") OR http_status>=500',
                [e for e in events if e.level in {"ERROR", "CRITICAL"} or (e.http_status or 0) >= 500],
                "low",
                "Always retain errors and 5xx responses.",
                ["high_http_error_rate", "payment_outage"],
            ),
            (
                "rec_preserve_security",
                "preserve",
                'scenario="credential_stuffing" OR event_type="failed_login"',
                [e for e in events if e.scenario == "credential_stuffing" or e.event_type == "failed_login"],
                "low",
                "Always retain security-relevant authentication events.",
                ["credential_stuffing"],
            ),
            (
                "rec_preserve_high_latency",
                "preserve",
                "duration_ms>=1500",
                [e for e in events if (e.duration_ms or 0) >= 1500],
                "low",
                "Always retain high-latency requests.",
                ["slow_payment_requests"],
            ),
            (
                "rec_preserve_privileged",
                "preserve",
                "is_privileged=true",
                [e for e in events if e.is_privileged],
                "low",
                "Always retain privileged-user events.",
                ["privileged_user_anomaly"],
            ),
            (
                "rec_preserve_rare_exceptions",
                "preserve",
                'scenario="rare_exception"',
                [e for e in events if e.scenario == "rare_exception"],
                "low",
                "Always retain rare application exceptions.",
                [],
            ),
        ]

        for rec_id, action, condition, matched, risk, reasoning, alerts in preserve_rules:
            recommendations.append(
                PolicyRecommendation(
                    id=rec_id,
                    action=action,
                    condition=condition,
                    affected_event_count=len(matched),
                    estimated_reduction=0,
                    risk_level=risk,
                    reasoning=reasoning,
                    spl_query=condition,
                    affected_saved_searches=alerts,
                )
            )

        total_reduction = sum(r.estimated_reduction for r in recommendations if r.action in {"drop", "sample"})
        proposal = ProposalRecord(
            analysis_id=analysis_id,
            recommendations=recommendations,
            total_reduction_estimate=total_reduction,
            total_reduction_percent=round(100 * total_reduction / max(total, 1), 2),
            intentional_demo_failure=False,
            notes="Policy proposal generated from real Splunk telemetry profile.",
        )

        action = AgentAction(
            timestamp=datetime.now(timezone.utc).isoformat(),
            agent="PolicyGenerator",
            action="generate_recommendations",
            source="local",
            detail=f"Generated {len(recommendations)} recommendations, estimated {total_reduction} event reduction",
        )
        return proposal, action