from __future__ import annotations
import asyncio
import os

from .ingestion import ingestion_service


async def main():
    interval = max(300, int(os.getenv("INGESTION_INTERVAL_SECONDS", "3600")))
    startup_delay = max(0, int(os.getenv("INGESTION_STARTUP_DELAY_SECONDS", "5")))
    await asyncio.sleep(startup_delay)
    while True:
        try:
            await ingestion_service.run_cycle()
        except Exception as exc:
            print(f"ingestion cycle failed: {type(exc).__name__}: {exc}", flush=True)
        await asyncio.sleep(interval)


if __name__ == "__main__":
    asyncio.run(main())
