from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.deps import set_storage
from app.main import app
from app.services.storage import Storage


def test_integrations_status(tmp_path):
    set_storage(Storage(data_dir=tmp_path / "data"))
    client = TestClient(app)
    resp = client.get("/api/integrations/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "splunk" in data
    assert "mcp" in data
    assert "splunk_connection" in data
    assert "ai" in data
    assert "connection_detail" in data
    assert "data_source" in data


def test_splunk_mcp_app_endpoint():
    client = TestClient(app)
    resp = client.get("/api/splunk/mcp-app")
    assert resp.status_code == 200
    data = resp.json()
    assert data["splunkbase_app_id"] == "7931"
    assert "install_steps" in data


def test_agents_catalog(tmp_path):
    set_storage(Storage(data_dir=tmp_path / "data"))
    client = TestClient(app)
    resp = client.get("/api/agents")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["agents"]) >= 8
    assert "timeline_actions" in data
    assert "active_agents" in data


def test_ai_status():
    client = TestClient(app)
    resp = client.get("/api/ai/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "configured" in data
    assert "available" in data


def test_list_analyses_empty(tmp_path):
    set_storage(Storage(data_dir=tmp_path / "data"))
    client = TestClient(app)
    resp = client.get("/api/analyses")
    assert resp.status_code == 200
    assert resp.json()["analyses"] == []