from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def connect_mongo():
    global _client, _db
    _client = AsyncIOMotorClient(settings.MONGODB_URL)
    _db = _client[settings.MONGODB_DB_NAME]
    await _db.checkpoints.create_index([("thread_id", 1), ("checkpoint_id", 1)])
    await _db.checkpoints.create_index([("thread_id", 1), ("step_index", -1)])


async def close_mongo():
    global _client
    if _client:
        _client.close()


def get_mongo_db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("MongoDB not connected – call connect_mongo() first")
    return _db
