from __future__ import annotations

AGENT_CATALOG = [
    {
        "id": "discovery",
        "name": "Discovery Agent",
        "phase": "analyze",
        "track": "observability",
        "description": "Connects to Splunk via MCP or API, inventories indexes, saved searches, and baseline telemetry volume.",
        "capabilities": ["get_splunk_info", "get_indexes", "get_saved_searches", "baseline_export"],
        "human_in_loop": False,
    },
    {
        "id": "profiler",
        "name": "Telemetry Profiler",
        "phase": "analyze",
        "track": "observability",
        "description": "Profiles services, event types, and scenarios to quantify reducible noise vs protected signal.",
        "capabilities": ["service_distribution", "category_distribution", "reducible_estimate"],
        "human_in_loop": False,
    },
    {
        "id": "protection",
        "name": "Protection Map Builder",
        "phase": "analyze",
        "track": "security",
        "description": "Maps events tied to critical detections so optimization never drops security-relevant telemetry.",
        "capabilities": ["detection_coverage_map", "protected_event_rules", "risk_scoring"],
        "human_in_loop": False,
    },
    {
        "id": "policy_generator",
        "name": "Policy Generator",
        "phase": "analyze",
        "track": "platform",
        "description": "Produces ingest filtering policies with reasoning, SPL evidence, and estimated byte reduction.",
        "capabilities": ["policy_recommendations", "spl_queries", "reduction_estimates"],
        "human_in_loop": True,
    },
    {
        "id": "policy_engine",
        "name": "Policy Engine",
        "phase": "apply",
        "track": "platform",
        "description": "Applies approved policies to baseline events and builds the optimized candidate dataset.",
        "capabilities": ["filter_apply", "candidate_build", "audit_trail"],
        "human_in_loop": False,
    },
    {
        "id": "replay_validator",
        "name": "Replay Validator",
        "phase": "validate",
        "track": "security",
        "description": "Replays real SPL saved searches against baseline and candidate indexes to prove detection coverage.",
        "capabilities": ["shadow_replay", "coverage_percent", "splunk_query_execution"],
        "human_in_loop": False,
    },
    {
        "id": "revision",
        "name": "Revision Agent",
        "phase": "revise",
        "track": "observability",
        "description": "Automatically relaxes policies when validation finds coverage regressions, then re-validates.",
        "capabilities": ["policy_revision", "coverage_recovery", "revalidation"],
        "human_in_loop": True,
    },
    {
        "id": "signalsmith_mentor",
        "name": "SignalSmith Mentor",
        "phase": "assist",
        "track": "platform",
        "description": "Direct in-product guide for SPL, pipeline steps, validation results, and safe policy decisions.",
        "capabilities": ["natural_language_spl", "chat", "session_context", "pipeline_coaching"],
        "human_in_loop": True,
    },
]


def agent_catalog() -> list[dict]:
    return AGENT_CATALOG