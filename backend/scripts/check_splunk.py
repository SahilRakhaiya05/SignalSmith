from __future__ import annotations

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
AUTH = (os.getenv("SPLUNK_USERNAME", ""), os.getenv("SPLUNK_PASSWORD", ""))
BASE = f"https://{os.getenv('SPLUNK_HOST', 'localhost')}:{os.getenv('SPLUNK_API_PORT', '8089')}"

with httpx.Client(verify=False, timeout=20) as c:
    for idx in ["signalsmith_baseline", "signalsmith_candidate"]:
        r = c.get(f"{BASE}/services/data/indexes/{idx}", params={"output_mode": "json"}, auth=AUTH)
        print(f"{idx}: {r.status_code}")

    r = c.get(f"{BASE}/services/data/inputs/http", params={"output_mode": "json"}, auth=AUTH)
    print(f"hec_inputs: {r.status_code}")
    if r.status_code == 200:
        for e in r.json().get("entry", []):
            print(" -", e.get("name"))