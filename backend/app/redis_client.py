import redis.asyncio as aioredis

from app.config import settings

_pool: aioredis.Redis | None = None

STREAM_MAX_LEN = 1000


async def connect_redis():
    global _pool
    _pool = aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def close_redis():
    global _pool
    if _pool:
        await _pool.aclose()


def get_redis() -> aioredis.Redis:
    if _pool is None:
        raise RuntimeError("Redis not connected – call connect_redis() first")
    return _pool


async def publish(channel: str, message: str):
    r = get_redis()
    # pub/sub for real-time fan-out; stream for durable replay by late-joining clients
    await r.publish(channel, message)
    stream_key = f"stream:{channel}"
    await r.xadd(stream_key, {"data": message}, maxlen=STREAM_MAX_LEN, approximate=True)


async def get_stream_history(channel: str, count: int = 100) -> list[str]:
    r = get_redis()
    stream_key = f"stream:{channel}"
    try:
        entries = await r.xrevrange(stream_key, count=count)
        messages = [entry[1]["data"] for entry in reversed(entries)]
        return messages
    except Exception:
        return []
