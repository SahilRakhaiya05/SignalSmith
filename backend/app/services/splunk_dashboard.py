from __future__ import annotations

import logging
import re
from typing import Any
from xml.sax.saxutils import escape

import httpx

from app.config import get_settings
from app.services.splunk_credentials import get_splunk_auth, get_splunk_username

logger = logging.getLogger(__name__)

DASHBOARD_NAME = "signalsmith_operations"
DASHBOARD_LABEL = "SignalSmith Operations"
SPLUNKBASE_MCP_URL = "https://splunkbase.splunk.com/app/7931"
DASHBOARD_APP = "search"


def _dashboard_xml(baseline: str, candidate: str) -> str:
    b, c = escape(baseline), escape(candidate)
    return f"""<dashboard version="1.1" theme="light">
  <label>{escape(DASHBOARD_LABEL)}</label>
  <description>Live telemetry optimization metrics from SignalSmith — baseline vs candidate indexes, service volume, and scenario distribution. Deployed by SignalSmith AI.</description>
  <row>
    <panel>
      <title>Index event volume</title>
      <chart>
        <search>
          <query>index={b} OR index={c} | stats count as count by index | sort -count</query>
          <earliest>-24h@h</earliest>
          <latest>now</latest>
        </search>
        <option name="charting.chart">column</option>
        <option name="charting.drilldown">none</option>
      </chart>
    </panel>
    <panel>
      <title>Baseline event count</title>
      <single>
        <search>
          <query>index={b} | stats count as count</query>
          <earliest>-24h@h</earliest>
          <latest>now</latest>
        </search>
        <option name="drilldown">none</option>
      </single>
    </panel>
  </row>
  <row>
    <panel>
      <title>Events by service (baseline)</title>
      <chart>
        <search>
          <query>index={b} | stats count as count by service | sort -count | head 12</query>
          <earliest>-24h@h</earliest>
          <latest>now</latest>
        </search>
        <option name="charting.chart">bar</option>
        <option name="charting.drilldown">all</option>
      </chart>
    </panel>
    <panel>
      <title>Events by scenario</title>
      <chart>
        <search>
          <query>index={b} | stats count as count by scenario | sort -count | head 10</query>
          <earliest>-24h@h</earliest>
          <latest>now</latest>
        </search>
        <option name="charting.chart">pie</option>
        <option name="charting.drilldown">none</option>
      </chart>
    </panel>
  </row>
  <row>
    <panel>
      <title>Log level distribution</title>
      <chart>
        <search>
          <query>index={b} | stats count as count by level | sort -count</query>
          <earliest>-24h@h</earliest>
          <latest>now</latest>
        </search>
        <option name="charting.chart">pie</option>
      </chart>
    </panel>
    <panel>
      <title>Health check noise (reducible)</title>
      <table>
        <search>
          <query>index={b} event_type=health_check | stats count as count by service | sort -count | head 10</query>
          <earliest>-24h@h</earliest>
          <latest>now</latest>
        </search>
        <option name="drilldown">cell</option>
      </table>
    </panel>
  </row>
  <row>
    <panel>
      <title>Candidate index by service</title>
      <chart>
        <search>
          <query>index={c} | stats count as count by service | sort -count | head 12</query>
          <earliest>-24h@h</earliest>
          <latest>now</latest>
        </search>
        <option name="charting.chart">bar</option>
      </chart>
    </panel>
    <panel>
      <title>Recent telemetry sample</title>
      <table>
        <search>
          <query>index={b} OR index={c} | head 20 | table _time index service event_type level scenario message</query>
          <earliest>-24h@h</earliest>
          <latest>now</latest>
        </search>
        <option name="count">20</option>
        <option name="drilldown">row</option>
      </table>
    </panel>
  </row>
</dashboard>"""


def _parse_splunk_error(text: str) -> str:
    match = re.search(r'<msg[^>]*>([^<]+)</msg>', text)
    return match.group(1).strip() if match else text[:200]


class SplunkDashboardService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _auth(self) -> tuple[str, str]:
        return get_splunk_auth()

    def splunk_web_url(self, path: str = "") -> str:
        return f"{self.settings.splunk_web_base}{path}"

    def dashboard_url(self, owner: str | None = None) -> str:
        """Web URL for the deployed Simple XML view (no query params — those break some Splunk builds)."""
        return self.splunk_web_url(f"/en-US/app/{DASHBOARD_APP}/{DASHBOARD_NAME}")

    def dashboard_browse_url(self) -> str:
        """Fallback: Splunk Dashboards listing in the Search app."""
        return self.splunk_web_url(f"/en-US/app/{DASHBOARD_APP}/dashboards")

    async def _session_key(self, client: httpx.AsyncClient) -> str:
        resp = await client.post(
            f"{self.settings.splunk_api_base}/services/auth/login",
            data={
                "username": get_splunk_username(),
                "password": get_splunk_auth()[1],
            },
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Splunk login failed (HTTP {resp.status_code}): {_parse_splunk_error(resp.text)}")
        match = re.search(r"<sessionKey>([^<]+)</sessionKey>", resp.text)
        if not match:
            raise RuntimeError("Splunk login succeeded but no session key was returned.")
        return match.group(1)

    async def _current_username(self, client: httpx.AsyncClient) -> str:
        resp = await client.get(
            f"{self.settings.splunk_api_base}/services/authentication/current-context",
            params={"output_mode": "json"},
            auth=self._auth(),
        )
        if resp.status_code == 200:
            entry = resp.json().get("entry", [{}])[0]
            username = entry.get("content", {}).get("username")
            if username:
                return username
        return get_splunk_username()

    def _deploy_owners(self, current_user: str) -> list[str]:
        owners: list[str] = ["nobody"]
        env_user = get_splunk_username()
        for candidate in (current_user, env_user):
            if candidate and candidate not in owners and candidate != "admin":
                owners.append(candidate)
        if env_user == "admin" and "admin" not in owners:
            owners.append("admin")
        return owners

    async def check_mcp_app(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "splunkbase_app_id": "7931",
            "splunkbase_url": SPLUNKBASE_MCP_URL,
            "app_name": None,
            "installed": False,
            "version": None,
            "mcp_endpoint": self.settings.splunk_mcp_endpoint,
            "mcp_reachable": False,
            "install_steps": [
                "Log in to Splunk Web as admin",
                f"Install Splunk MCP Server from {SPLUNKBASE_MCP_URL}",
                "Restart Splunk after installation",
                "Grant mcp_tool_execute capability to your role in Settings → Access controls",
                "Re-run: python backend/scripts/check_mcp.py",
            ],
        }
        try:
            async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
                resp = await client.get(
                    f"{self.settings.splunk_api_base}/services/apps/local",
                    params={"output_mode": "json", "count": 0, "search": "mcp"},
                    auth=self._auth(),
                )
                if resp.status_code == 200:
                    for entry in resp.json().get("entry", []):
                        name = entry.get("name", "")
                        if "mcp" in name.lower():
                            content = entry.get("content", {})
                            result["installed"] = True
                            result["app_name"] = name
                            result["version"] = content.get("version") or content.get("label")
                            break

                mcp_headers = {"Content-Type": "application/json"}
                mcp_auth = self._auth()
                if self.settings.splunk_mcp_token:
                    mcp_headers["Authorization"] = f"Bearer {self.settings.splunk_mcp_token}"
                    mcp_auth = None
                mcp_resp = await client.post(
                    result["mcp_endpoint"],
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {"client": "SignalSmith", "version": "3.0"},
                    },
                    headers=mcp_headers,
                    auth=mcp_auth,
                    timeout=10.0,
                )
                result["mcp_reachable"] = mcp_resp.status_code == 200
                if mcp_resp.status_code == 200:
                    try:
                        data = mcp_resp.json()
                        server = data.get("result", {}).get("serverInfo", {})
                        result["mcp_server_name"] = server.get("name")
                        result["mcp_server_version"] = server.get("version")
                    except Exception:
                        pass
        except Exception as exc:
            result["error"] = str(exc)
        return result

    def dashboard_xml(self) -> str:
        return _dashboard_xml(
            self.settings.splunk_baseline_index,
            self.settings.splunk_candidate_index,
        )

    async def dashboard_status(self) -> dict[str, Any]:
        status: dict[str, Any] = {
            "name": DASHBOARD_NAME,
            "label": DASHBOARD_LABEL,
            "deployed": False,
            "owner": None,
            "url": self.dashboard_url(),
            "browse_url": self.dashboard_browse_url(),
            "splunk_web": self.splunk_web_url(),
            "app": DASHBOARD_APP,
        }
        try:
            async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
                session_key = await self._session_key(client)
                headers = {"Authorization": f"Splunk {session_key}"}
                current_user = await self._current_username(client)
                for owner in self._deploy_owners(current_user):
                    resp = await client.get(
                        f"{self.settings.splunk_api_base}/servicesNS/{owner}/{DASHBOARD_APP}/data/ui/views/{DASHBOARD_NAME}",
                        params={"output_mode": "json"},
                        headers=headers,
                    )
                    if resp.status_code == 200:
                        status["deployed"] = True
                        status["owner"] = owner
                        entry = resp.json().get("entry", [{}])[0]
                        status["label"] = entry.get("content", {}).get("label", DASHBOARD_LABEL)
                        break
        except Exception as exc:
            status["error"] = str(exc)
        return status

    async def deploy_dashboard(self) -> dict[str, Any]:
        baseline = self.settings.splunk_baseline_index
        candidate = self.settings.splunk_candidate_index
        xml = _dashboard_xml(baseline, candidate)

        last_error = ""
        async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
            session_key = await self._session_key(client)
            headers = {"Authorization": f"Splunk {session_key}"}
            current_user = await self._current_username(client)
            owners = self._deploy_owners(current_user)

            for owner in owners:
                base_path = (
                    f"{self.settings.splunk_api_base}/servicesNS/{owner}/{DASHBOARD_APP}/data/ui/views"
                )
                existing = await client.get(
                    f"{base_path}/{DASHBOARD_NAME}",
                    headers=headers,
                )
                if existing.status_code == 200:
                    resp = await client.post(
                        f"{base_path}/{DASHBOARD_NAME}",
                        data={"eai:data": xml},
                        headers=headers,
                    )
                    action = "updated"
                elif existing.status_code == 404:
                    resp = await client.post(
                        base_path,
                        data={"name": DASHBOARD_NAME, "eai:data": xml},
                        headers=headers,
                    )
                    action = "created"
                else:
                    last_error = (
                        f"owner={owner} lookup HTTP {existing.status_code}: "
                        f"{_parse_splunk_error(existing.text)}"
                    )
                    continue

                if resp.status_code < 400:
                    return {
                        "status": action,
                        "name": DASHBOARD_NAME,
                        "owner": owner,
                        "url": self.dashboard_url(owner),
                        "browse_url": self.dashboard_browse_url(),
                        "message": (
                            f"Splunk dashboard '{DASHBOARD_LABEL}' {action}. "
                            f"In Splunk Web go to Search → Dashboards → {DASHBOARD_LABEL}."
                        ),
                    }
                last_error = f"owner={owner} HTTP {resp.status_code}: {_parse_splunk_error(resp.text)}"

        raise RuntimeError(
            "Dashboard deploy failed. Ensure your Splunk user can edit dashboards in the Search app. "
            f"Authenticated as '{current_user}'. {last_error}"
        )