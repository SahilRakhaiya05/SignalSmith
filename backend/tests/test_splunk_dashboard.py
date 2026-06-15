from __future__ import annotations

import httpx
import pytest

from app.services.splunk_dashboard import DASHBOARD_NAME, SplunkDashboardService


def test_deploy_owners_prefers_nobody_and_skips_admin_for_dev_user():
    svc = SplunkDashboardService()
    svc.settings.splunk_username = "dev"
    owners = svc._deploy_owners("dev")
    assert owners[0] == "nobody"
    assert "dev" in owners
    assert "admin" not in owners


def test_dashboard_url_has_no_query_params():
    svc = SplunkDashboardService()
    url = svc.dashboard_url()
    assert "?" not in url
    assert url.endswith("/signalsmith_operations")
    assert svc.dashboard_browse_url().endswith("/dashboards")


def test_deploy_owners_includes_admin_when_configured():
    svc = SplunkDashboardService()
    svc.settings.splunk_username = "admin"
    owners = svc._deploy_owners("admin")
    assert owners == ["nobody", "admin"]


@pytest.mark.asyncio
async def test_deploy_dashboard_uses_session_key_without_label_param(monkeypatch):
    svc = SplunkDashboardService()
    posted: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path.endswith("/servicesNS/nobody/search/data/ui/views"):
            posted.append(request.content.decode())
            return httpx.Response(201, text="<response/>")
        if request.url.path.endswith(f"/servicesNS/nobody/search/data/ui/views/{DASHBOARD_NAME}"):
            return httpx.Response(404, text="<response/>")
        return httpx.Response(500, text="unexpected")

    transport = httpx.MockTransport(handler)

    class PatchedClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr("app.services.splunk_dashboard.httpx.AsyncClient", PatchedClient)
    monkeypatch.setattr(svc, "_session_key", lambda _client: _return("test-session"))
    monkeypatch.setattr(svc, "_current_username", lambda _client: _return("dev"))

    result = await svc.deploy_dashboard()
    assert result["status"] == "created"
    assert result["owner"] == "nobody"
    assert posted
    assert "label=" not in posted[0]
    assert f"name={DASHBOARD_NAME}" in posted[0]


async def _return(value):
    return value