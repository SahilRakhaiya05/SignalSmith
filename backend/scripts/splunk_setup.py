from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

HOST = os.getenv("SPLUNK_HOST", "localhost")
API_PORT = os.getenv("SPLUNK_API_PORT", "8089")
HEC_PORT = os.getenv("SPLUNK_HEC_PORT", "8088")
USER = os.getenv("SPLUNK_USERNAME", "admin")
PWD = os.getenv("SPLUNK_PASSWORD", "")
HEC_TOKEN = os.getenv("SPLUNK_HEC_TOKEN", "")
BASELINE = os.getenv("SPLUNK_BASELINE_INDEX", "signalsmith_baseline")
CANDIDATE = os.getenv("SPLUNK_CANDIDATE_INDEX", "signalsmith_candidate")

API_BASE = f"https://{HOST}:{API_PORT}"
HEC_URL = f"https://{HOST}:{HEC_PORT}/services/collector/event"
AUTH = (USER, PWD)


def main() -> int:
    print(f"Splunk host: {HOST}")
    print(f"Web UI port: {os.getenv('SPLUNK_WEB_PORT', '8001')}")
    print(f"API port: {API_PORT}")

    with httpx.Client(verify=False, timeout=30.0) as client:
        resp = client.get(f"{API_BASE}/services/server/info", params={"output_mode": "json"}, auth=AUTH)
        print(f"REST API: {resp.status_code}")
        if resp.status_code != 200:
            print(resp.text[:300])
            return 1

        for index in (BASELINE, CANDIDATE):
            create = client.post(
                f"{API_BASE}/services/data/indexes",
                params={"name": index},
                auth=AUTH,
            )
            check = client.get(
                f"{API_BASE}/services/data/indexes/{index}",
                params={"output_mode": "json"},
                auth=AUTH,
            )
            status = "exists" if check.status_code == 200 else f"create={create.status_code}"
            print(f"Index {index}: {status}")

        if HEC_TOKEN:
            hec_resp = client.post(
                HEC_URL,
                headers={"Authorization": f"Splunk {HEC_TOKEN}"},
                json={"event": {"signalsmith": "setup_test", "source": "signalsmith_setup"}},
            )
            print(f"HEC test: {hec_resp.status_code} {hec_resp.text[:120]}")
        else:
            print("HEC token not set - ingestion will use local fallback")

    print("Splunk setup check complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())