from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_storage, set_storage
from app.main import app
from app.services.storage import Storage
from tests.conftest import seed_baseline_events


@pytest.fixture
def client(tmp_path: Path):
    set_storage(Storage(data_dir=tmp_path / "data"))
    return TestClient(app)


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "SignalSmith AI"
    assert "splunk_connection" in data


def test_session_workflow(client):
    storage = get_storage()
    seed_baseline_events(storage, event_count=5000, seed=42)

    assert client.post("/api/session/reset").status_code == 200
    seed_baseline_events(storage, event_count=5000, seed=42)

    start = client.post("/api/analysis/start")
    assert start.status_code == 200
    analysis_id = start.json()["analysis_id"]
    assert start.json()["status"] == "completed"

    analysis = client.get(f"/api/analysis/{analysis_id}").json()
    assert analysis["status"] == "completed"

    proposal = client.get(f"/api/proposals/{analysis_id}").json()
    proposal_id = proposal["id"]
    apply_resp = client.post(f"/api/proposals/{proposal_id}/apply")
    assert apply_resp.status_code == 200

    validation = client.post(f"/api/validation/{proposal_id}/run").json()
    assert validation["status"] == "passed"
    assert validation["protected_events_lost"] == 0
    approve = client.post(f"/api/proposals/{proposal_id}/approve")
    assert approve.status_code == 200

    otel = client.get(f"/api/proposals/{proposal_id}/export/otel")
    assert otel.status_code == 200
    assert "WARNING" in otel.text

    audit = client.get("/api/audit")
    assert audit.status_code == 200
    assert len(audit.json()["entries"]) > 0