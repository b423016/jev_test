from __future__ import annotations

import json
import logging

log = logging.getLogger("jev")

TTL_SECONDS = 7 * 24 * 60 * 60


class ScreenCache:
    def __init__(self, redis_url: str):
        self._redis = None
        if not redis_url:
            return
        try:
            import redis

            client = redis.Redis.from_url(redis_url, socket_timeout=2, socket_connect_timeout=2)
            client.ping()
            self._redis = client
        except Exception:
            log.warning("redis unavailable; screen cache is off")

    def get(self, content_hash: str, document_type: str) -> dict | None:
        if self._redis is None:
            return None
        raw = self._redis.get(_key(content_hash, document_type))
        if not raw:
            return None
        return json.loads(raw)

    def put(self, content_hash: str, document_type: str, screen: dict) -> None:
        if self._redis is None:
            return
        self._redis.set(
            _key(content_hash, document_type),
            json.dumps(screen),
            ex=TTL_SECONDS,
        )


def _key(content_hash: str, document_type: str) -> str:
    return f"screen:{document_type}:{content_hash}"
