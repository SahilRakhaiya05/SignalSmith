import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.analysis_orchestrator import AnalysisOrchestrator
from app.services.storage import Storage


async def main() -> None:
    storage = Storage()
    analysis = storage.get_latest_analysis()
    if not analysis:
        print("No analysis found")
        return
    proposal = storage.get_proposal_by_analysis(analysis.id)
    if not proposal:
        print("No proposal found")
        return

    orchestrator = AnalysisOrchestrator(storage)
    candidate = storage.load_events("candidate_events.json")
    if not candidate:
        print("Applying proposal first...")
        await orchestrator.apply_proposal(proposal.id)
        proposal = storage.get_proposal(proposal.id) or proposal

    print(f"Running validation for proposal {proposal.id[:8]}...")
    validation = await orchestrator.run_validation(proposal.id, run_number=1)
    print(f"status={validation.status.value} mode={validation.mode} passed={validation.tests_passed}/{validation.tests_total}")
    for r in validation.coverage_results:
        print(
            f"  {r.search_name}: baseline={r.baseline_count} candidate={r.candidate_count} "
            f"method={r.validation_method} passed={r.passed}"
        )


if __name__ == "__main__":
    asyncio.run(main())