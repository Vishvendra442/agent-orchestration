import logging
import threading
from typing import Any, Optional

from pymongo import MongoClient

from app.config import settings
from app.mongo import get_mongo_db

logger = logging.getLogger(__name__)

_sync_client_lock = threading.Lock()
_sync_client: MongoClient | None = None
_sync_checkpointer = None


def get_sync_checkpointer():
    """Process-local singleton — safe from ProcessPoolExecutor workers."""
    global _sync_client, _sync_checkpointer

    if _sync_checkpointer is not None:
        return _sync_checkpointer

    with _sync_client_lock:
        if _sync_checkpointer is not None:
            return _sync_checkpointer

        from langgraph.checkpoint.mongodb import MongoDBSaver

        _sync_client = MongoClient(
            settings.MONGODB_URL,
            maxPoolSize=10,
            serverSelectionTimeoutMS=5000,
        )
        _sync_checkpointer = MongoDBSaver(_sync_client, db_name=settings.MONGODB_DB_NAME)
        logger.info("Created process-local MongoDBSaver (pid=%s)", __import__("os").getpid())
        return _sync_checkpointer


class MongoDBCheckpointer:

    def __init__(self):
        self.collection_name = "checkpoints"

    @property
    def _col(self):
        db = get_mongo_db()
        return db[self.collection_name]

    async def list_checkpoints(self, thread_id: str) -> list[dict[str, Any]]:
        cursor = self._col.find(
            {"thread_id": thread_id},
            {"_id": 0},
        ).sort("checkpoint_id", -1)
        results = []
        async for doc in cursor:
            results.append({
                "thread_id": doc.get("thread_id"),
                "checkpoint_id": doc.get("checkpoint_id"),
                "checkpoint_ns": doc.get("checkpoint_ns", ""),
                "metadata": doc.get("metadata"),
            })
        return results

    async def get_checkpoint(self, thread_id: str, checkpoint_id: str) -> Optional[dict]:
        doc = await self._col.find_one(
            {"thread_id": thread_id, "checkpoint_id": checkpoint_id},
            {"_id": 0},
        )
        return doc

    async def delete_checkpoints(self, thread_id: str) -> int:
        result = await self._col.delete_many({"thread_id": thread_id})
        return result.deleted_count
