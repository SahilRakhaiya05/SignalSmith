from __future__ import annotations

import httpx

from app.config import get_settings


class SplunkAuthService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def verify(self, username: str, password: str) -> tuple[bool, str, dict]:
        user = username.strip()
        pwd = password.strip()
        if not user or not pwd:
            return False, "Username and password are required.", {}

        base = self.settings.splunk_api_base
        try:
            async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
                info = await client.get(
                    f"{base}/services/server/info",
                    params={"output_mode": "json"},
                    auth=(user, pwd),
                )
                if info.status_code == 200:
                    data = info.json()
                    entry = (data.get("entry") or [{}])[0]
                    content = entry.get("content", {})
                    return True, "Authenticated", {
                        "username": user,
                        "server_name": content.get("serverName"),
                        "version": content.get("version"),
                    }

                login = await client.post(
                    f"{base}/services/auth/login",
                    data={"username": user, "password": pwd},
                )
                if login.status_code == 200 and "sessionKey" in login.text:
                    return True, "Authenticated", {"username": user}

                if info.status_code == 401:
                    return False, "Invalid Splunk username or password.", {}
                return False, f"Splunk login failed (HTTP {info.status_code}).", {}
        except httpx.ConnectError:
            return False, (
                f"Cannot reach Splunk at {base}. Check SPLUNK_HOST and SPLUNK_API_PORT in .env."
            ), {}
        except Exception as exc:
            return False, f"Splunk authentication error: {exc}", {}