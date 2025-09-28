from __future__ import annotations

import json
from typing import Any, Optional

from redis.asyncio import Redis


CONVERSATION_TTL_SECONDS = 300
CONVERSATION_CACHE_LIMIT = 50


def conversation_key(user_a: int, user_b: int) -> str:
    a, b = sorted((user_a, user_b))
    return f"conv:{a}:{b}"


async def get_conversation_cache(
    redis: Redis[str], user_a: int, user_b: int, limit: int, offset: int
) -> Optional[list[dict[str, Any]]]:
    key = conversation_key(user_a, user_b)
    raw = await redis.get(key)
    if raw is None:
        return None
    try:
        items: list[dict[str, Any]] = json.loads(raw)
    except Exception:
        return None
    # Newest first expected
    slice_ = items[offset : offset + limit]
    return slice_


async def push_conversation_cache(
    redis: Redis[str], user_a: int, user_b: int, message: dict[str, Any]
) -> None:
    key = conversation_key(user_a, user_b)
    raw = await redis.get(key)
    items: list[dict[str, Any]] = []
    if raw:
        try:
            items = json.loads(raw)
        except Exception:
            items = []
    # Insert at head (newest first)
    items.insert(0, message)
    if len(items) > CONVERSATION_CACHE_LIMIT:
        items = items[:CONVERSATION_CACHE_LIMIT]
    await redis.set(key, json.dumps(items), ex=CONVERSATION_TTL_SECONDS)


async def set_conversation_cache(
    redis: Redis[str], user_a: int, user_b: int, messages: list[dict[str, Any]]
) -> None:
    key = conversation_key(user_a, user_b)
    await redis.set(
        key, json.dumps(messages[:CONVERSATION_CACHE_LIMIT]), ex=CONVERSATION_TTL_SECONDS
    )
