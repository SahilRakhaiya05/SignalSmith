from __future__ import annotations

from app.agents.profiler import TelemetryProfiler
from app.services.telemetry_generator import TelemetryGenerator


def test_pattern_profiling():
    events = TelemetryGenerator(seed=42, event_count=2000).generate()
    profiler = TelemetryProfiler()
    summary, action = profiler.profile(events)
    assert summary["total_events"] == 2000
    assert summary["total_bytes"] > 0
    assert len(summary["patterns"]) > 0
    assert "auth-service" in summary["by_service"]
    assert summary["reducible_estimate"] > 0
    assert action.agent == "TelemetryProfiler"