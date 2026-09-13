from __future__ import annotations
import asyncio
import os
from contextlib import suppress
from .ingestion import ingestion_service


class IngestionScheduler:
    def __init__(self):
        self._task: asyncio.Task | None = None
        self.interval_seconds = int(os.getenv("INGESTION_INTERVAL_SECONDS", "21600"))  # 6h
        self.enabled = os.getenv("AUTO_INGESTION_ENABLED", "true").lower() in {"1", "true", "yes"}

    async def _loop(self):
        # Run once shortly after startup, then on the configured interval.
        await asyncio.sleep(2)
        while True:
            try:
                await ingestion_service.run_cycle()
            except Exception:
                pass
            await asyncio.sleep(self.interval_seconds)

    def start(self):
        if self.enabled and self._task is None:
            self._task = asyncio.create_task(self._loop())

    async def stop(self):
        if self._task:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None


scheduler = IngestionScheduler()
