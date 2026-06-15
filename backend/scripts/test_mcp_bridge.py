from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.mcp_client import SplunkMCPClient


async def main() -> None:
    client = SplunkMCPClient()
    mode = await client.initialize()
    print("mode:", mode)
    indexes, src = await client.list_indexes()
    print(f"indexes ({src}):", len(indexes), indexes[:5])
    spl, spl_src = await client.generate_spl("health check volume by service")
    print(f"generate_spl ({spl_src}):", spl[:100])
    count, cnt_src = await client.run_search_count("index=signalsmith_baseline | stats count")
    print(f"count ({cnt_src}):", count)
    print("status:", client.status_dict())


if __name__ == "__main__":
    asyncio.run(main())