from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.telemetry_generator import TelemetryGenerator

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "samples"
SAMPLES.mkdir(exist_ok=True)

events = TelemetryGenerator(seed=42, event_count=250).generate()
(SAMPLES / "demo_baseline_events.json").write_text(
    json.dumps([e.model_dump() for e in events], indent=2),
    encoding="utf-8",
)

detections = [
    {
        "name": "Payment Outage",
        "spl": 'index=$INDEX$ service="payment-service" (level="ERROR" OR http_status>=500) scenario="payment_outage"',
    },
    {
        "name": "High HTTP Error Rate",
        "spl": "index=$INDEX$ http_status>=500",
    },
    {
        "name": "Slow Payment Requests",
        "spl": 'index=$INDEX$ service="payment-service" duration_ms>=1500',
    },
    {
        "name": "Credential Stuffing",
        "spl": 'index=$INDEX$ scenario="credential_stuffing" OR (service="auth-service" event_type="failed_login" http_status=401)',
    },
    {
        "name": "Privileged User Login Anomaly",
        "spl": 'index=$INDEX$ is_privileged=true service="auth-service" event_type="login"',
    },
]
(SAMPLES / "detections.json").write_text(json.dumps(detections, indent=2), encoding="utf-8")
print(f"Wrote {len(events)} events to {SAMPLES}")