from __future__ import annotations

from app.agents.policy_generator import PolicyGenerator
from app.agents.profiler import TelemetryProfiler
from app.services.otel_export import generate_otel_yaml, generate_rollback_yaml
from app.services.telemetry_generator import TelemetryGenerator


def test_yaml_export_contains_required_sections():
    events = TelemetryGenerator(seed=42, event_count=1000).generate()
    profile, _ = TelemetryProfiler().profile(events)
    proposal, _ = PolicyGenerator().generate("a1", events, profile)
    otel = generate_otel_yaml(proposal)
    rollback = generate_rollback_yaml(proposal)
    assert "WARNING" in otel
    assert "health_check" in otel
    assert "debug_heartbeat" in otel
    assert "probabilistic_sampler" in otel
    assert "preserve_privileged" in otel
    assert "rollback" in rollback.lower() or "rollback: true" in rollback.lower()