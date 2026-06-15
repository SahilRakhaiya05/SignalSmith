from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
API = "http://127.0.0.1:8080"


def call(method: str, path: str, body: dict | None = None) -> dict:
    with httpx.Client(timeout=600.0) as client:
        resp = client.request(method, f"{API}{path}", json=body)
        resp.raise_for_status()
        if "application/json" in resp.headers.get("content-type", ""):
            return resp.json()
        return {"text": resp.text}


def main() -> int:
    print("==> Health")
    health = call("GET", "/api/health")
    print(json.dumps(health, indent=2))

    print("==> Reset")
    call("POST", "/api/demo/reset")

    print("==> Generate 20,000 events")
    gen = call("POST", "/api/demo/generate", {"event_count": 20000, "seed": 42})
    print(f"Generated {gen['event_count']} events ({gen['total_bytes']} bytes)")

    print("==> Ingest baseline to Splunk (this may take a few minutes)")
    start = time.time()
    ingest = call("POST", "/api/demo/ingest-baseline")
    print(f"Ingested {ingest.get('ingested')}/{ingest.get('event_count')} via {ingest.get('mode')} in {time.time()-start:.1f}s")

    print("==> Run agent analysis")
    analysis = call("POST", "/api/analysis/start")
    analysis_id = analysis["analysis_id"]
    detail = call("GET", f"/api/analysis/{analysis_id}")
    print(f"Analysis {analysis_id}: mode={detail['mode']}, events={detail['baseline_event_count']}")

    proposal = call("GET", f"/api/proposals/{analysis_id}")
    proposal_id = proposal["id"]
    print(f"Proposal {proposal_id} with {len(proposal['recommendations'])} recommendations")

    print("==> Apply proposal")
    applied = call("POST", f"/api/proposals/{proposal_id}/apply")
    print(f"Candidate events: {applied['candidate_event_count']}")

    print("==> Validation run 1 (expect failure)")
    v1 = call("POST", f"/api/validation/{proposal_id}/run")
    print(f"Run 1: {v1['status']}, deliberate_failure={v1['deliberate_failure']}, protected_lost={v1['protected_events_lost']}")

    print("==> Revise and validation run 2")
    revised = call("POST", f"/api/validation/{v1['id']}/revise")
    v2 = revised["validation"]
    print(f"Run 2: {v2['status']}, reduction={v2['event_reduction_percent']}%, coverage={v2['coverage_percent']}%")

    print("==> Approve")
    call("POST", f"/api/proposals/{proposal_id}/approve")

    print("\nDemo complete!")
    print("  UI:      http://localhost:5173")
    print("  API:     http://localhost:8080/docs")
    print("  Splunk:  http://localhost:8001")
    print(f"  Indexes: signalsmith_baseline, signalsmith_candidate")
    return 0


if __name__ == "__main__":
    sys.exit(main())