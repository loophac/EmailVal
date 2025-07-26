import aioredis
import time

redis = aioredis.from_url("redis://localhost", decode_responses=True)

TIER_LIMITS = {
    "free": 60,
    "pro": 300,
    "unlimited": 500
}

async def is_rate_limited(api_key: str, tier: str) -> bool:
    now = int(time.time()) // 60  # Current minute bucket
    key = f"rate:{api_key}:{now}"
    limit = TIER_LIMITS.get(tier, 60)

    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 60)
    return count > limit
