from __future__ import annotations

import pytest

from app.agents.policy_engine import PolicyEngine
from app.agents.policy_generator import PolicyGenerator
from app.agents.profiler import TelemetryProfiler
from app.agents.replay_validator import ReplayValidator
from app.agents.revision_agent import RevisionAgent
from app.models.proposals import PolicyRecommendation
from app.models.validation import SearchCoverageResult, ValidationRecord, ValidationStatus
from app.services.splunk_client import SplunkClient
from app.services.telemetry_generator import TelemetryGenerator


@pytest.mark.asyncio
async def test_production_validation_passes():
    events = TelemetryGenerator(seed=42, event_count=5000).generate()
    profile, _ = TelemetryProfiler().profile(events)
    proposal, _ = PolicyGenerator().generate("a1", events, profile)
    surviving, _ = PolicyEngine().apply(events, proposal)
    validator = ReplayValidator(SplunkClient())
    validation = await validator.validate(proposal, events, surviving, run_number=1)
    assert validation.status.value == "passed"
    assert validation.deliberate_failure is False
    assert validation.protected_events_lost == 0


def test_revision_removes_failing_sample_rules():
    events = TelemetryGenerator(seed=42, event_count=5000).generate()
    profile, _ = TelemetryProfiler().profile(events)
    proposal, _ = PolicyGenerator().generate("a1", events, profile)
    proposal.recommendations.append(
        PolicyRecommendation(
            id="rec_bad_sample",
            action="sample",
            condition='service="auth-service"',
            affected_event_count=100,
            estimated_reduction=80,
            risk_level="high",
            reasoning="Aggressive sampling that breaks privileged-user detection.",
            spl_query='service="auth-service" | sample 0.05',
            affected_saved_searches=["privileged_user_anomaly"],
            parameters={"sample_rate": 0.05},
        )
    )
    validation = ValidationRecord(
        proposal_id=proposal.id,
        status=ValidationStatus.FAILED,
        coverage_results=[
            SearchCoverageResult(
                search_id="privileged_user_anomaly",
                search_name="Privileged user anomaly",
                baseline_count=5,
                candidate_count=0,
                baseline_triggered=True,
                candidate_triggered=False,
                passed=False,
            )
        ],
    )
    revised, detail = RevisionAgent().revise(proposal, validation)
    assert "rec_bad_sample" not in [r.id for r in revised.recommendations]
    assert "rec_bad_sample" in detail or "regression" in detail.lower()