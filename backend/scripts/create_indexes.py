from __future__ import annotations

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
AUTH = (os.getenv("SPLUNK_USERNAME", ""), os.getenv("SPLUNK_PASSWORD", ""))
BASE = f"https://{os.getenv('SPLUNK_HOST', 'localhost')}:{os.getenv('SPLUNK_API_PORT', '8089')}"
INDEXES = [
    os.getenv("SPLUNK_BASELINE_INDEX", "signalsmith_baseline"),
    os.getenv("SPLUNK_CANDIDATE_INDEX", "signalsmith_candidate"),
]

with httpx.Client(verify=False, timeout=30) as c:
    for idx in INDEXES:
        check = c.get(f"{BASE}/services/data/indexes/{idx}", auth=AUTH)
        if check.status_code == 200:
            print(f"{idx}: already exists")
            continue
        resp = c.post(
            f"{BASE}/services/data/indexes",
            data={"name": idx},
            auth=AUTH,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        print(f"{idx}: create status {resp.status_code}")
        if resp.status_code not in (200, 201):
            print(resp.text[:500])