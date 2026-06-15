from __future__ import annotations

import os
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
AUTH = (os.getenv("SPLUNK_USERNAME", ""), os.getenv("SPLUNK_PASSWORD", ""))
BASE = f"https://{os.getenv('SPLUNK_HOST', 'localhost')}:{os.getenv('SPLUNK_API_PORT', '8089')}"

searches = {
    "baseline": f"search index={os.getenv('SPLUNK_BASELINE_INDEX')} | stats count",
    "candidate": f"search index={os.getenv('SPLUNK_CANDIDATE_INDEX')} | stats count",
}

with httpx.Client(verify=False, timeout=120) as c:
    for label, search in searches.items():
        create = c.post(
            f"{BASE}/services/search/jobs",
            data={"search": search, "exec_mode": "oneshot", "output_mode": "json"},
            auth=AUTH,
        )
        print(f"{label}: job status {create.status_code}")
        if create.status_code == 200 and "count" in create.text:
            import re
            m = re.search(r'"count":\s*"(\d+)"', create.text)
            print(f"  events: {m.group(1) if m else 'pending'}")
        else:
            print(f"  {create.text[:200]}")