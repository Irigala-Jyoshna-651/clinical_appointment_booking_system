from __future__ import annotations

import time
from contextlib import contextmanager


class StageTimer:
    def __init__(self, target_ms: int = 450):
        self.target_ms = target_ms
        self._stages: dict[str, float] = {}
        self._started_at = time.perf_counter()

    @contextmanager
    def stage(self, name: str):
        start = time.perf_counter()
        yield
        elapsed = (time.perf_counter() - start) * 1000
        self._stages[name] = round(elapsed, 2)

    def snapshot(self, include_total: bool = False) -> dict[str, float]:
        payload = dict(self._stages)
        if include_total:
            payload["total"] = round((time.perf_counter() - self._started_at) * 1000, 2)
            payload["target"] = float(self.target_ms)
        return payload
