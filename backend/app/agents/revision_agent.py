from __future__ import annotations

from datetime import datetime, timezone

from app.agents.policy_generator import PolicyGenerator
from app.models.proposals import PolicyRecommendation, ProposalRecord, ProposalStatus
from app.models.validation import ValidationRecord


class RevisionAgent:
    def revise(
        self,
        proposal: ProposalRecord,
        validation: ValidationRecord,
    ) -> tuple[ProposalRecord, str]:
        """Revise failed policy to retain privileged-user events and remove aggressive login sampling."""
        if validation.status.value != "failed":
            return proposal, "No revision needed"

        revised_recs: list[PolicyRecommendation] = []
        revision_detail_parts: list[str] = []

        failed_search_ids = {
            r.search_id for r in validation.coverage_results if not r.passed
        }

        for rec in proposal.recommendations:
            if rec.action == "sample" and any(s in failed_search_ids for s in rec.affected_saved_searches):
                revision_detail_parts.append(
                    f"Removed sampling rule {rec.id} that caused detection regression."
                )
                continue
            revised_recs.append(rec)

        privileged_rec = next((r for r in revised_recs if r.id == "rec_preserve_privileged"), None)
        if privileged_rec:
            privileged_rec.reasoning = (
                "Revised: privileged-user events are always retained with highest priority."
            )
            privileged_rec.risk_level = "low"
            revision_detail_parts.append("Strengthened privileged-user preservation rule.")

        proposal.recommendations = revised_recs
        proposal.version += 1
        proposal.intentional_demo_failure = False
        proposal.notes = "Revised after validation failure: privileged-user events always retained."
        proposal.total_reduction_estimate = sum(
            r.estimated_reduction for r in revised_recs if r.action in {"drop", "sample"}
        )
        total_events = proposal.total_reduction_estimate + sum(
            r.affected_event_count - r.estimated_reduction
            for r in revised_recs
            if r.action in {"drop", "sample"}
        )
        if total_events > 0:
            proposal.total_reduction_percent = round(
                100 * proposal.total_reduction_estimate / total_events, 2
            )

        detail = " ".join(revision_detail_parts) or "Policy revised based on validation regression."
        return proposal, detail