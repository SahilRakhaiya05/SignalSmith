from __future__ import annotations

from app.agents.protection_map import ProtectionMapBuilder
from app.services.telemetry_generator import TelemetryGenerator


def test_protection_rules():
    events = TelemetryGenerator(seed=42, event_count=3000).generate()
    builder = ProtectionMapBuilder()
    protection_map, action = builder.build(events)
    rule_ids = {p["rule_id"] for p in protection_map}
    assert "error_critical" in rule_ids
    assert "privileged_user" in rule_ids
    assert "credential_stuffing" in rule_ids
    assert any(p["rule_id"].startswith("saved_search_") for p in protection_map)
    assert action.agent == "ProtectionMapBuilder"


def test_privileged_events_protected():
    events = TelemetryGenerator(seed=42, event_count=5000).generate()
    builder = ProtectionMapBuilder()
    privileged = [e for e in events if e.is_privileged]
    assert privileged
    for event in privileged:
        protected, reason = builder.is_protected(event)
        assert protected
        assert reason