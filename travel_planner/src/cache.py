import os

import redis.asyncio as aioredis

redis: aioredis.Redis | None = None


async def init() -> None:
    global redis
    redis = aioredis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True,
    )

async def close() -> None:
    if redis:
        await redis.aclose()

def get() -> aioredis.Redis:
    if redis is None:
        raise RuntimeError("Redis client is not initialized")
    return redis
