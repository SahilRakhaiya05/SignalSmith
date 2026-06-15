from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.splunk_client import SplunkClient
from app.services.storage import Storage


async def main() -> None:
    storage = Storage(data_dir=Path(__file__).resolve().parents[1] / "data")
    events = storage.load_events("candidate_events.json")
    client = SplunkClient()
    connected, mode = await client.connect()
    print(f"Connected: {connected} ({mode})")
    if not connected:
        return
    await client.ensure_indexes()
    ingested, ingest_mode = await client.ingest_events(client.settings.splunk_candidate_index, events)
    print(f"Ingested {ingested}/{len(events)} to {client.settings.splunk_candidate_index} via {ingest_mode}")


if __name__ == "__main__":
    asyncio.run(main())