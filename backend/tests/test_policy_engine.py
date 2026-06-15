from __future__ import annotations

from app.agents.policy_engine import PolicyEngine
from app.agents.policy_generator import PolicyGenerator
from app.agents.profiler import TelemetryProfiler
from app.services.telemetry_generator import TelemetryGenerator


def test_policy_application_reduces_events():
    events = TelemetryGenerator(seed=42, event_count=5000).generate()
    profiler = TelemetryProfiler()
    profile, _ = profiler.profile(events)
    generator = PolicyGenerator()
    proposal, _ = generator.generate("test-analysis", events, profile)

    engine = PolicyEngine()
    surviving, _ = engine.apply(events, proposal)
    assert len(surviving) < len(events)


def test_baseline_not_mutated(temp_storage):
    events = TelemetryGenerator(seed=42, event_count=1000).generate()
    temp_storage.save_events("baseline_events.json", events)
    original = temp_storage.load_events("baseline_events.json")

    profiler = TelemetryProfiler()
    profile, _ = profiler.profile(original)
    proposal, _ = PolicyGenerator().generate("a1", original, profile)
    surviving, _ = PolicyEngine().apply(original, proposal)
    temp_storage.save_events("candidate_events.json", surviving)

    reloaded = temp_storage.load_events("baseline_events.json")
    assert len(reloaded) == len(original)
    assert [e.trace_id for e in reloaded] == [e.trace_id for e in original]