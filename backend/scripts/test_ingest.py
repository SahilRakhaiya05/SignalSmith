from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
AUTH = (os.getenv("SPLUNK_USERNAME", ""), os.getenv("SPLUNK_PASSWORD", ""))
HOST = os.getenv("SPLUNK_HOST", "localhost")
API = os.getenv("SPLUNK_API_PORT", "8089")
HEC = os.getenv("SPLUNK_HEC_PORT", "8088")
TOKEN = os.getenv("SPLUNK_HEC_TOKEN", "")
INDEX = os.getenv("SPLUNK_BASELINE_INDEX", "signalsmith_baseline")
EVENT = {"service": "auth-service", "level": "INFO", "message": "signalsmith ingest test"}

tests = [
    ("hec_8088", f"https://{HOST}:{HEC}/services/collector/event"),
    ("mgmt_collector", f"https://{HOST}:{API}/services/collector/event"),
    ("receiver_simple", f"https://{HOST}:{API}/services/receivers/simple"),
]

with httpx.Client(verify=False, timeout=15) as c:
    for name, url in tests:
        try:
            if "collector" in url:
                r = c.post(
                    url,
                    headers={"Authorization": f"Splunk {TOKEN}"},
                    json={"index": INDEX, "event": EVENT},
                )
            else:
                r = c.post(
                    url,
                    params={"index": INDEX, "sourcetype": "signalsmith:telemetry", "source": "test"},
                    content=json.dumps(EVENT),
                    auth=AUTH,
                    headers={"Content-Type": "application/json"},
                )
            print(name, r.status_code, r.text[:100])
        except Exception as exc:
            print(name, "error", exc)