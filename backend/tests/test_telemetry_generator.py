from __future__ import annotations

from app.services.telemetry_generator import TelemetryGenerator


def test_deterministic_generation():
    gen1 = TelemetryGenerator(seed=42, event_count=1000)
    gen2 = TelemetryGenerator(seed=42, event_count=1000)
    events1 = gen1.generate()
    events2 = gen2.generate()
    assert len(events1) == 1000
    assert [e.trace_id for e in events1] == [e.trace_id for e in events2]


def test_event_schema_fields():
    events = TelemetryGenerator(seed=42, event_count=100).generate()
    for event in events:
        assert event.timestamp
        assert event.service in {"auth-service", "checkout-service", "payment-service", "inventory-service"}
        assert event.environment == "production"
        assert event.level
        assert event.event_type
        assert event.message
        assert event.trace_id
        assert event.scenario
        assert event.estimated_size_bytes > 0


def test_default_event_count():
    events = TelemetryGenerator(seed=42).generate()
    assert len(events) == 20000


def test_scenarios_present():
    events = TelemetryGenerator(seed=42, event_count=5000).generate()
    scenarios = {e.scenario for e in events}
    expected = {
        "normal_traffic",
        "health_check",
        "debug_heartbeat",
        "payment_outage",
        "http_500",
        "slow_checkout",
        "failed_login",
        "credential_stuffing",
        "privileged_anomaly",
        "rare_exception",
    }
    assert expected.issubset(scenarios)