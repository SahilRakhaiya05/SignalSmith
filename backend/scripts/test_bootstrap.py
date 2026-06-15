from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.splunk_data_service import SplunkDataService


async def main() -> None:
    svc = SplunkDataService()
    result = await svc.bootstrap_baseline()
    print("index:", result["index"])
    print("splunk_count:", result["event_count"])
    print("exported:", len(result["events"]))
    print("profile services:", list(result["profile"]["by_service"].keys())[:5])


if __name__ == "__main__":
    asyncio.run(main())