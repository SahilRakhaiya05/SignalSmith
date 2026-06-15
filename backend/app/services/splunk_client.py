from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_INGEST_OK = {200, 201, 204}

from app.config import get_settings
from app.services.splunk_credentials import get_splunk_auth
from app.models.events import TelemetryEvent
from app.services.saved_searches import get_active_saved_searches, saved_search_catalog


class SplunkClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.connected = False
        self.mode = "offline"
        self.ingest_mode = "splunk_api"

    async def connect(self) -> tuple[bool, str]:
        try:
            async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
                response = await client.get(
                    f"{self.settings.splunk_api_base}/services/server/info",
                    params={"output_mode": "json"},
                    auth=get_splunk_auth(),
                )
                if response.status_code == 200:
                    self.connected = True
                    self.mode = "splunk_api"
                    self.ingest_mode = await self._detect_ingest_mode()
                    return True, "splunk_api"
        except Exception:
            pass

        self.connected = False
        self.mode = "offline"
        return False, "offline"

    async def _detect_ingest_mode(self) -> str:
        if not self.settings.splunk_hec_token:
            return "rest_receiver"
        try:
            async with httpx.AsyncClient(verify=False, timeout=3.0) as client:
                resp = await client.post(
                    self.settings.splunk_hec_url,
                    headers={"Authorization": f"Splunk {self.settings.splunk_hec_token}"},
                    json={"event": {"signalsmith": "probe"}},
                )
                if resp.status_code in _INGEST_OK:
                    return "hec"
        except Exception:
            pass
        return "rest_receiver"

    async def ensure_indexes(self) -> list[str]:
        indexes = [self.settings.splunk_baseline_index, self.settings.splunk_candidate_index]
        if not self.connected:
            return indexes

        for index in indexes:
            await self._create_index_if_missing(index)
        return indexes

    async def _create_index_if_missing(self, index_name: str) -> None:
        if not self.connected:
            return
        auth = get_splunk_auth()
        try:
            async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
                check = await client.get(f"{self.settings.splunk_api_base}/services/data/indexes/{index_name}", auth=auth)
                if check.status_code == 200:
                    return
                await client.post(
                    f"{self.settings.splunk_api_base}/services/data/indexes",
                    data={"name": index_name},
                    auth=auth,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
        except Exception:
            pass

    async def ingest_events(
        self,
        index: str,
        events: list[TelemetryEvent],
        source: str = "signalsmith:generator",
    ) -> tuple[int, str]:
        if not self.connected or not events:
            return len(events), "local"

        if self.ingest_mode == "hec" and self.settings.splunk_hec_token:
            ingested = await self._ingest_via_hec(index, events, source=source)
            if ingested:
                return ingested, "splunk_api"

        ingested = await self._ingest_via_rest_receiver(index, events, source=source)
        return ingested, "splunk_api"

    async def _ingest_via_hec(self, index: str, events: list[TelemetryEvent], source: str = "signalsmith:generator") -> int:
        headers = {"Authorization": f"Splunk {self.settings.splunk_hec_token}"}
        batch_size = 500
        ingested = 0
        async with httpx.AsyncClient(verify=False, timeout=120.0) as client:
            for i in range(0, len(events), batch_size):
                batch = events[i : i + batch_size]
                body = "\n".join(
                    json.dumps(
                        {
                            "index": index,
                            "source": source,
                            "event": e.to_splunk_payload(),
                            "sourcetype": "signalsmith:telemetry",
                        }
                    )
                    for e in batch
                )
                try:
                    resp = await client.post(
                        self.settings.splunk_hec_url,
                        headers={**headers, "Content-Type": "application/json"},
                        content=body,
                    )
                    if resp.status_code in _INGEST_OK:
                        ingested += len(batch)
                except Exception:
                    break
        return ingested

    async def _ingest_via_rest_receiver(
        self,
        index: str,
        events: list[TelemetryEvent],
        source: str = "signalsmith:generator",
    ) -> int:
        stream_url = f"{self.settings.splunk_api_base}/services/receivers/stream"
        simple_url = f"{self.settings.splunk_api_base}/services/receivers/simple"
        params = {
            "index": index,
            "sourcetype": "signalsmith:telemetry",
            "source": source,
        }
        auth = get_splunk_auth()
        batch_size = 100
        ingested = 0

        async with httpx.AsyncClient(verify=False, timeout=120.0) as client:
            for i in range(0, len(events), batch_size):
                batch = events[i : i + batch_size]
                body = "\n".join(json.dumps(e.to_splunk_payload()) for e in batch)
                try:
                    resp = await client.post(
                        stream_url,
                        params=params,
                        content=body,
                        auth=auth,
                        headers={"Content-Type": "application/json"},
                    )
                    if resp.status_code in _INGEST_OK:
                        ingested += len(batch)
                        continue
                except Exception:
                    pass

                for event in batch:
                    try:
                        resp = await client.post(
                            simple_url,
                            params=params,
                            content=json.dumps(event.to_splunk_payload()),
                            auth=auth,
                            headers={"Content-Type": "application/json"},
                        )
                        if resp.status_code in _INGEST_OK:
                            ingested += 1
                    except Exception:
                        break

        return ingested

    async def get_indexes(self) -> tuple[list[str], str]:
        if not self.connected:
            return [
                self.settings.splunk_baseline_index,
                self.settings.splunk_candidate_index,
            ], "offline"

        try:
            async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
                resp = await client.get(
                    f"{self.settings.splunk_api_base}/services/data/indexes",
                    params={"output_mode": "json", "count": 0},
                    auth=get_splunk_auth(),
                )
                if resp.status_code == 200:
                    data = resp.json()
                    entries = data.get("entry", [])
                    names = [e.get("name", "") for e in entries if e.get("name")]
                    return names, "splunk_api"
        except Exception:
            pass
        return [self.settings.splunk_baseline_index, self.settings.splunk_candidate_index], "offline"

    def get_saved_searches(self) -> tuple[list[dict[str, Any]], str]:
        return saved_search_catalog(), "offline" if not self.connected else "splunk_api"

    def saved_search_definitions(self) -> list:
        return get_active_saved_searches()

    async def run_search_count(self, spl: str) -> tuple[int, str]:
        from app.services.splunk_data_service import _extract_count, spl_for_count

        if not self.connected:
            return 0, "offline"
        count_spl = spl_for_count(spl)
        search = count_spl if count_spl.strip().lower().startswith("search") else f"search {count_spl}"
        try:
            async with httpx.AsyncClient(verify=False, timeout=120.0) as client:
                resp = await client.post(
                    f"{self.settings.splunk_api_base}/services/search/jobs/oneshot",
                    data={"search": search, "output_mode": "json", "count": 0},
                    auth=get_splunk_auth(),
                )
                if resp.status_code == 200:
                    try:
                        return _extract_count(resp.json()), "splunk_spl"
                    except Exception:
                        return _extract_count(resp.text), "splunk_spl"
                logger.warning("Splunk search failed status=%s", resp.status_code)
        except Exception as exc:
            logger.warning("Splunk search error: %s", exc)
        return 0, "fallback"

    async def count_index_events(self, index: str) -> int:
        count, _ = await self.run_search_count(f"index={index} | stats count as count | fields count")
        return count

    async def health_report(self) -> dict[str, Any]:
        report: dict[str, Any] = {
            "host": self.settings.splunk_host,
            "api_port": self.settings.splunk_api_port,
            "api_scheme": self.settings.splunk_api_scheme,
            "web_port": self.settings.splunk_web_port,
            "web_scheme": self.settings.splunk_web_scheme,
            "web_url": self.settings.splunk_web_base,
            "api_url": self.settings.splunk_api_base,
            "mcp_endpoint": self.settings.splunk_mcp_endpoint,
            "hec_port": self.settings.splunk_hec_port,
            "baseline_index": self.settings.splunk_baseline_index,
            "candidate_index": self.settings.splunk_candidate_index,
            "rest_api": {"reachable": False},
            "hec": {"configured": bool(self.settings.splunk_hec_token), "reachable": False},
            "indexes": {},
            "ingest_mode": self.ingest_mode,
        }
        connected, mode = await self.connect()
        report["mode"] = mode
        report["rest_api"]["reachable"] = connected
        if not connected:
            return report

        for idx in (self.settings.splunk_baseline_index, self.settings.splunk_candidate_index):
            try:
                async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
                    resp = await client.get(
                        f"{self.settings.splunk_api_base}/services/data/indexes/{idx}",
                        params={"output_mode": "json"},
                        auth=get_splunk_auth(),
                    )
                    exists = resp.status_code == 200
                    count = await self.count_index_events(idx) if exists else 0
                    report["indexes"][idx] = {"exists": exists, "event_count": count}
            except Exception as exc:
                report["indexes"][idx] = {"exists": False, "error": str(exc)}

        if self.settings.splunk_hec_token:
            try:
                async with httpx.AsyncClient(verify=False, timeout=3.0) as client:
                    resp = await client.post(
                        self.settings.splunk_hec_url,
                        headers={"Authorization": f"Splunk {self.settings.splunk_hec_token}"},
                        json={"event": {"probe": True}},
                    )
                    report["hec"]["reachable"] = resp.status_code in (200, 201)
            except Exception:
                report["hec"]["reachable"] = False

        return report

    async def run_search(self, spl: str) -> tuple[int, str]:
        return await self.run_search_count(spl)

    def document_saved_searches(self) -> str:
        lines = ["# SignalSmith Saved Searches", ""]
        for s in get_active_saved_searches():
            lines.append(f"## {s.name}")
            lines.append(s.description)
            lines.append(f"```spl\n{s.spl_template}\n```")
            lines.append("")
        return "\n".join(lines)