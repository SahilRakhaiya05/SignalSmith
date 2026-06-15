from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.agents.protection_map import ProtectionMapBuilder
from app.models.events import TelemetryEvent
from app.models.proposals import ProposalRecord
from app.models.validation import SearchCoverageResult, ValidationRecord, ValidationStatus
from app.services.mcp_client import SplunkMCPClient
from app.services.saved_searches import get_active_saved_searches, run_saved_search
from app.services.splunk_client import SplunkClient


class ReplayValidator:
    def __init__(self, splunk: SplunkClient, mcp: SplunkMCPClient | None = None) -> None:
        self.splunk = splunk
        self.mcp = mcp or SplunkMCPClient()
        self.protection = ProtectionMapBuilder()

    async def validate(
        self,
        proposal: ProposalRecord,
        baseline_events: list[TelemetryEvent],
        candidate_events: list[TelemetryEvent],
        run_number: int = 1,
    ) -> ValidationRecord:
        mcp_mode = await self.mcp.initialize()
        if not self.splunk.connected:
            await self.splunk.connect()

        use_real_splunk = self.splunk.connected or mcp_mode in {"splunk_mcp", "splunk_api"}
        mode = mcp_mode if mcp_mode == "splunk_mcp" else (self.splunk.mode if self.splunk.connected else "offline")

        validation_source = f"signalsmith:replay-{proposal.id[:8]}-r{run_number}-{uuid4().hex[:8]}"
        if self.splunk.connected:
            await self.splunk.ensure_indexes()
            await self.splunk.ingest_events(
                self.splunk.settings.splunk_candidate_index,
                candidate_events,
                source=validation_source,
            )

        coverage_results: list[SearchCoverageResult] = []
        tests_passed = 0

        active_searches = get_active_saved_searches()
        for search in active_searches:
            local_baseline = run_saved_search(baseline_events, search)
            local_candidate = run_saved_search(candidate_events, search)
            method = "local"
            baseline_count = local_baseline
            candidate_count = local_candidate

            if use_real_splunk:
                source_filter = f' source="{validation_source}"'
                candidate_spl = search.spl_for_index(self.splunk.settings.splunk_candidate_index) + source_filter
                spl_candidate, c_src = await self.mcp.run_search_count(candidate_spl)
                baseline_count = local_baseline
                if spl_candidate > 0 or local_candidate == 0:
                    candidate_count = spl_candidate
                    method = c_src if spl_candidate > 0 else "local"
                else:
                    candidate_count = local_candidate
                    method = "local"
                if spl_candidate > 0:
                    method = f"local+{c_src}"

            baseline_triggered = baseline_count >= search.trigger_threshold
            candidate_triggered = candidate_count >= search.trigger_threshold
            passed = baseline_triggered == candidate_triggered and (
                not baseline_triggered or candidate_count >= search.trigger_threshold
            )
            if search.importance in {"critical", "high"} and baseline_triggered and not candidate_triggered:
                passed = False

            if passed:
                tests_passed += 1

            detail = (
                f"Baseline: {baseline_count}, Candidate: {candidate_count}, "
                f"Threshold: {search.trigger_threshold} ({method})"
            )
            coverage_results.append(
                SearchCoverageResult(
                    search_id=search.id,
                    search_name=search.name,
                    baseline_count=baseline_count,
                    candidate_count=candidate_count,
                    baseline_triggered=baseline_triggered,
                    candidate_triggered=candidate_triggered,
                    passed=passed,
                    importance=search.importance,
                    detail=detail,
                    validation_method=method,
                )
            )

        baseline_count = len(baseline_events)
        candidate_count = len(candidate_events)
        baseline_bytes = sum(e.estimated_size_bytes for e in baseline_events)
        candidate_bytes = sum(e.estimated_size_bytes for e in candidate_events)

        protected_lost = self._count_protected_lost(baseline_events, candidate_events)
        coverage_percent = round(100 * tests_passed / max(len(active_searches), 1), 2)
        event_reduction = round(100 * (1 - candidate_count / max(baseline_count, 1)), 2)
        byte_reduction = round(100 * (1 - candidate_bytes / max(baseline_bytes, 1)), 2)

        failed_results = [r for r in coverage_results if not r.passed]
        failure_reason = None
        if failed_results:
            failure_reason = "; ".join(f"{r.search_name}: {r.detail}" for r in failed_results)

        all_passed = tests_passed == len(active_searches) and protected_lost == 0
        status = ValidationStatus.PASSED if all_passed else ValidationStatus.FAILED

        risk = "low" if all_passed else "high" if protected_lost > 0 else "medium"

        return ValidationRecord(
            proposal_id=proposal.id,
            run_number=run_number,
            status=status,
            mode=mode,
            baseline_event_count=baseline_count,
            candidate_event_count=candidate_count,
            event_reduction_percent=event_reduction,
            byte_reduction_percent=byte_reduction,
            coverage_percent=coverage_percent,
            protected_events_lost=protected_lost,
            tests_passed=tests_passed,
            tests_total=len(active_searches),
            final_risk_level=risk,
            coverage_results=coverage_results,
            deliberate_failure=False,
            failure_reason=failure_reason,
        )

    def _count_protected_lost(
        self,
        baseline: list[TelemetryEvent],
        candidate: list[TelemetryEvent],
    ) -> int:
        candidate_traces = {e.trace_id for e in candidate}
        lost = 0
        for event in baseline:
            protected, _ = self.protection.is_protected(event)
            if protected and event.trace_id not in candidate_traces:
                lost += 1
        return lost