from __future__ import annotations

import json
from typing import Any

import redis


class SessionMemoryStore:
    def __init__(self, redis_url: str, ttl_seconds: int = 1800):
        self.ttl_seconds = ttl_seconds
        self._redis = None
        try:
            self._redis = redis.Redis.from_url(redis_url, decode_responses=True)
            self._redis.ping()
        except Exception:
            self._redis = None
        self._fallback: dict[str, dict[str, Any]] = {}

    def get(self, session_id: str) -> dict[str, Any]:
        if self._redis:
            raw = self._redis.get(f"session:{session_id}")
            return json.loads(raw) if raw else {}
        return self._fallback.get(session_id, {}).copy()

    def set(self, session_id: str, data: dict[str, Any]) -> None:
        if self._redis:
            self._redis.setex(f"session:{session_id}", self.ttl_seconds, json.dumps(data))
            return
        self._fallback[session_id] = data.copy()
