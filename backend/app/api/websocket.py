import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.redis_client import get_redis, get_stream_history

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/monitoring/{execution_id}")
async def execution_log_stream(websocket: WebSocket, execution_id: str):
    await websocket.accept()
    logger.info("WebSocket connected for execution %s", execution_id)

    channel = f"execution:{execution_id}:logs"

    try:
        history = await get_stream_history(channel)
        for msg in history:
            await websocket.send_text(msg)
            try:
                parsed = json.loads(msg)
                if parsed.get("type") == "execution_finished":
                    await websocket.send_text(json.dumps({"type": "stream_end"}))
                    return
            except json.JSONDecodeError:
                pass

        redis = get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)

        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=5.0)
                if message and message["type"] == "message":
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    await websocket.send_text(data)

                    try:
                        parsed = json.loads(data)
                        if parsed.get("type") == "execution_finished":
                            await websocket.send_text(json.dumps({"type": "stream_end"}))
                            break
                    except json.JSONDecodeError:
                        pass
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for execution %s", execution_id)
    except Exception as exc:
        logger.exception("WebSocket error for execution %s: %s", execution_id, exc)
