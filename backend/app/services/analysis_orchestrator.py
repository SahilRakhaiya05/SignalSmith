from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.agents.discovery import DiscoveryAgent
from app.agents.policy_engine import PolicyEngine
from app.agents.policy_generator import PolicyGenerator
from app.agents.profiler import TelemetryProfiler
from app.agents.protection_map import ProtectionMapBuilder
from app.agents.replay_validator import ReplayValidator
from app.agents.revision_agent import RevisionAgent
from app.config import get_settings
from app.models.analysis import AnalysisRecord, AnalysisStatus
from app.models.proposals import ProposalRecord, ProposalStatus
from app.models.validation import ValidationRecord, ValidationStatus
from app.services.audit_log import AuditLogService
from app.services.mcp_client import SplunkMCPClient
from app.services.splunk_client import SplunkClient
from app.services.storage import Storage


class AnalysisOrchestrator:
    def __init__(self, storage: Storage) -> None:
        self.storage = storage
        self.audit = AuditLogService(storage)
        self.splunk = SplunkClient()
        self.mcp = SplunkMCPClient()
        self.discovery = DiscoveryAgent(storage, self.audit, self.splunk, self.mcp)
        self.profiler = TelemetryProfiler()
        self.protection = ProtectionMapBuilder()
        self.policy_gen = PolicyGenerator()
        self.policy_engine = PolicyEngine(debug=get_settings().debug_policy_audit)
        self.validator = ReplayValidator(self.splunk, self.mcp)
        self.revision = RevisionAgent()

    async def run_analysis(self, analysis_id: str) -> AnalysisRecord:
        record = self.storage.get_analysis(analysis_id)
        if not record:
            raise ValueError(f"Analysis {analysis_id} not found")

        try:
            record.status = AnalysisStatus.RUNNING
            record.progress = 0.1
            record.message = "Starting discovery..."
            self.storage.save_analysis(record)

            discovery, timeline, mode = await self.discovery.discover(analysis_id)
            record.mode = mode
            record.agent_timeline.extend(timeline)
            record.saved_searches = discovery["saved_searches"]
            record.baseline_event_count = discovery["baseline_event_count"]
            record.baseline_bytes = discovery["baseline_bytes"]
            record.progress = 0.3
            self.storage.save_analysis(record)

            events = self.storage.load_events("baseline_events.json")
            if not events:
                raise ValueError("No baseline events found. Generate and ingest first.")

            profile, profile_action = self.profiler.profile(events)
            record.profile_summary = profile
            record.services = list(profile["by_service"].keys())
            record.event_types = list(profile["by_event_type"].keys())
            record.reducible_estimate = profile["reducible_estimate"]
            record.agent_timeline.append(profile_action)
            record.progress = 0.55
            self.storage.save_analysis(record)

            protection_map, protect_action = self.protection.build(events)
            record.protection_map = protection_map
            record.agent_timeline.append(protect_action)
            record.progress = 0.75
            self.storage.save_analysis(record)

            proposal, gen_action = self.policy_gen.generate(analysis_id, events, profile)
            record.agent_timeline.append(gen_action)
            self.storage.save_proposal(proposal)
            self.audit.record(
                actor="PolicyGenerator",
                action="create_proposal",
                source="local",
                output_summary=f"proposal_id={proposal.id}",
                analysis_id=analysis_id,
                proposal_id=proposal.id,
            )

            record.progress = 1.0
            record.status = AnalysisStatus.COMPLETED
            record.message = "Analysis complete"
            self.storage.save_analysis(record)
            return record
        except Exception as exc:
            record.status = AnalysisStatus.FAILED
            record.error = str(exc)
            record.message = f"Analysis failed: {exc}"
            self.storage.save_analysis(record)
            raise

    async def apply_proposal(self, proposal_id: str) -> ProposalRecord:
        proposal = self.storage.get_proposal(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")

        baseline = self.storage.load_events("baseline_events.json")
        surviving, _ = self.policy_engine.apply(baseline, proposal)
        self.storage.save_events("candidate_events.json", surviving)
        proposal.status = ProposalStatus.APPLIED
        self.storage.save_proposal(proposal)
        self.audit.record(
            actor="PolicyEngine",
            action="apply_proposal",
            source="local",
            input_summary=f"baseline={len(baseline)}",
            output_summary=f"candidate={len(surviving)}",
            proposal_id=proposal_id,
            analysis_id=proposal.analysis_id,
        )
        return proposal

    async def run_validation(self, proposal_id: str, run_number: int | None = None) -> ValidationRecord:
        proposal = self.storage.get_proposal(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")

        baseline = self.storage.load_events("baseline_events.json")
        candidate = self.storage.load_events("candidate_events.json")
        if not candidate:
            raise ValueError("No candidate events. Apply proposal first.")

        existing = self.storage.get_validations_for_proposal(proposal_id)
        run_num = run_number or (len(existing) + 1)
        validation = await self.validator.validate(
            proposal,
            baseline,
            candidate,
            run_number=run_num,
        )
        self.storage.save_validation(validation)
        self.audit.record(
            actor="ReplayValidator",
            action="run_validation",
            source=validation.mode,
            output_summary=f"status={validation.status.value}, passed={validation.tests_passed}/{validation.tests_total}",
            proposal_id=proposal_id,
            analysis_id=proposal.analysis_id,
        )
        return validation

    async def revise_and_revalidate(self, validation_id: str) -> tuple[ProposalRecord, ValidationRecord]:
        validation = self.storage.get_validation(validation_id)
        if not validation:
            raise ValueError(f"Validation {validation_id} not found")

        proposal = self.storage.get_proposal(validation.proposal_id)
        if not proposal:
            raise ValueError("Proposal not found")

        revised_proposal, detail = self.revision.revise(proposal, validation)
        self.storage.save_proposal(revised_proposal)

        validation.revision_applied = True
        validation.revision_detail = detail
        validation.status = ValidationStatus.REVISED
        self.storage.save_validation(validation)

        await self.apply_proposal(revised_proposal.id)
        second_validation = await self.run_validation(revised_proposal.id, run_number=2)

        self.audit.record(
            actor="RevisionAgent",
            action="revise_policy",
            source="local",
            output_summary=detail,
            proposal_id=proposal.id,
            analysis_id=proposal.analysis_id,
        )
        return revised_proposal, second_validation