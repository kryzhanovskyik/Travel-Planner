import json
from typing import Optional

import httpx

from src.cache import get as get_redis

BASE_URL = "https://api.artic.edu/api/v1/artworks"
TTL = 24 * 60 * 60     # 24 hours


async def validate_artwork(external_id: int) -> Optional[dict]:
    """Fetch artwork data from the Art Institute of Chicago API with 24h cache. Returns None if not found."""
    redis = get_redis()
    key = f"artwork:{external_id}"

    cached = await redis.get(key)
    if cached is not None:
        return json.loads(cached)

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                f"{BASE_URL}/{external_id}",
                params={"fields": "id,title"},
            )
        except httpx.RequestError:
            return None

    if response.status_code == 404:
        return None

    if not response.is_success:
        return None

    payload = response.json()
    artwork = payload.get("data")
    if artwork:
        await redis.set(key, json.dumps(artwork), ex=TTL)

    return artwork
