"""
GraphMind — Async Redis client wrapper.
Handles connection lifecycle, mindmap caching, semantic query caching,
and cache invalidation on writes.
"""

import hashlib
import json
import logging
from typing import Optional

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

# ── Cache TTLs (seconds) ──
MINDMAP_TTL = 300        # 5 minutes
SEMANTIC_CACHE_TTL = 600  # 10 minutes


class RedisClient:
    """Thin async wrapper around redis.asyncio."""

    def __init__(self) -> None:
        self._redis: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        self._redis = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        await self._redis.ping()
        logger.info("Redis connected at %s", settings.redis_url)

    async def close(self) -> None:
        if self._redis:
            await self._redis.aclose()
            logger.info("Redis connection closed")

    @property
    def r(self) -> aioredis.Redis:
        if not self._redis:
            raise RuntimeError("Redis not connected — call connect() first")
        return self._redis

    # ────────────────────────────────────────────────────────
    #  Mindmap Cache   key = "mindmap:{user_id}"
    # ────────────────────────────────────────────────────────

    async def get_mindmap(self, user_id: str) -> Optional[str]:
        """Return cached mindmap JSON string or None."""
        try:
            return await self.r.get(f"mindmap:{user_id}")
        except Exception as e:
            logger.warning("Redis GET mindmap failed: %s", e)
            return None

    async def set_mindmap(self, user_id: str, payload: str) -> None:
        """Cache mindmap JSON string with TTL."""
        try:
            await self.r.set(f"mindmap:{user_id}", payload, ex=MINDMAP_TTL)
        except Exception as e:
            logger.warning("Redis SET mindmap failed: %s", e)

    async def invalidate_mindmap(self, user_id: str) -> None:
        """Evict mindmap cache after graph writes."""
        try:
            await self.r.delete(f"mindmap:{user_id}")
        except Exception as e:
            logger.warning("Redis DEL mindmap failed: %s", e)

    # ────────────────────────────────────────────────────────
    #  Semantic Query Cache   key = "qcache:{user_id}:{hash}"
    # ────────────────────────────────────────────────────────

    @staticmethod
    def _query_hash(query: str) -> str:
        normalized = query.strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()[:24]

    async def get_query_cache(self, user_id: str, query: str) -> Optional[str]:
        """Return cached LLM response JSON for an identical query, or None."""
        key = f"qcache:{user_id}:{self._query_hash(query)}"
        try:
            return await self.r.get(key)
        except Exception as e:
            logger.warning("Redis GET query cache failed: %s", e)
            return None

    async def set_query_cache(
        self, user_id: str, query: str, payload: str
    ) -> None:
        """Cache LLM response JSON for a query."""
        key = f"qcache:{user_id}:{self._query_hash(query)}"
        try:
            await self.r.set(key, payload, ex=SEMANTIC_CACHE_TTL)
        except Exception as e:
            logger.warning("Redis SET query cache failed: %s", e)

    async def invalidate_user_caches(self, user_id: str) -> None:
        """Evict ALL caches for a user (mindmap + query caches)."""
        try:
            keys = []
            async for key in self.r.scan_iter(match=f"*:{user_id}*", count=200):
                keys.append(key)
            if keys:
                await self.r.delete(*keys)
                logger.debug("Invalidated %d cache keys for user %s", len(keys), user_id)
        except Exception as e:
            logger.warning("Redis invalidation failed: %s", e)


# Singleton
redis_client = RedisClient()
