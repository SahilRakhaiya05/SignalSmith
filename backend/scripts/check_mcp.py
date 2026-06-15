from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings


def main() -> int:
    settings = get_settings()
    auth = (settings.splunk_username, settings.splunk_password)
    base = settings.splunk_api_base
    web = settings.splunk_web_base
    mcp_url = settings.splunk_mcp_endpoint

    print("SignalSmith MCP Check")
    print("Splunk API:", base)
    print("Splunk Web:", web)
    print("Splunkbase: https://splunkbase.splunk.com/app/7931")
    print()

    mcp_installed = False
    apps = httpx.get(
        f"{base}/services/apps/local",
        params={"output_mode": "json", "count": 0},
        auth=auth,
        verify=False,
        timeout=15,
    )
    print("Apps status:", apps.status_code)
    if apps.status_code == 200:
        for entry in apps.json().get("entry", []):
            name = entry.get("name", "")
            if "mcp" in name.lower():
                mcp_installed = True
                version = entry.get("content", {}).get("version", "?")
                print(f"  MCP app: {name} (v{version})")

    if not mcp_installed:
        print("  MCP app: NOT INSTALLED")
        print()
        print("Install Splunk MCP Server from Splunkbase app 7931:")
        print("  1. Open Splunk Web -> Apps -> Find More Apps")
        print("  2. Search 'MCP Server' and install")
        print("  3. Restart Splunk")
        print("  4. Grant mcp_tool_execute to your role")

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"client": "SignalSmith", "version": "3.0"},
    }
    headers = {"Content-Type": "application/json"}
    if settings.splunk_mcp_token:
        headers["Authorization"] = f"Bearer {settings.splunk_mcp_token}"
        mcp_auth = None
    else:
        mcp_auth = auth
    resp = httpx.post(mcp_url, json=payload, auth=mcp_auth, headers=headers, verify=False, timeout=15)
    print()
    print("MCP URL:", mcp_url)
    print("MCP status:", resp.status_code)

    if resp.status_code == 200:
        try:
            data = resp.json()
            server = data.get("result", {}).get("serverInfo", {})
            print("MCP server:", server.get("name"), server.get("version"))
            print()
            print("SUCCESS: Official Splunk MCP Server is active.")
            return 0
        except json.JSONDecodeError:
            print(resp.text[:500])
    else:
        print(resp.text[:500])
        print()
        if mcp_installed:
            print("App is installed but MCP endpoint returned", resp.status_code)
            if "bearer token" in resp.text.lower():
                print("Create an MCP Encrypted Token in Splunk MCP Server and set SPLUNK_MCP_TOKEN in .env")
            else:
                print("Check role capabilities (mcp_tool_execute) and restart Splunk.")
        else:
            print("SignalSmith will use Splunk API fallback until app 7931 is installed.")

    return 1


if __name__ == "__main__":
    raise SystemExit(main())