import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.redis_client import get_redis
from app.services.telegram_service import (
    get_telegram_agent_config,
    invoke_agent_for_telegram,
    send_message,
    set_webhook,
)
from app.services.message_service import save_message

logger = logging.getLogger(__name__)

router = APIRouter()

TELEGRAM_DEDUP_TTL = 3600


@router.post("/webhook")
async def telegram_webhook(update: dict[str, Any], db: AsyncSession = Depends(get_db)):
    message = update.get("message")
    if not message:
        return {"ok": True, "detail": "no message in update"}

    update_id = update.get("update_id")
    if update_id:
        redis = get_redis()
        dedup_key = f"telegram:update:{update_id}"
        already_processed = await redis.set(dedup_key, "1", nx=True, ex=TELEGRAM_DEDUP_TTL)
        if not already_processed:
            logger.info("Duplicate Telegram update_id=%s, skipping", update_id)
            return {"ok": True, "detail": "duplicate update, already processed"}

    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")
    user_info = message.get("from", {})

    if not chat_id or not text:
        return {"ok": True, "detail": "no chat_id or text"}

    agent_config = await get_telegram_agent_config(db)
    if not agent_config:
        logger.warning("No agent configured for Telegram channel")
        await send_message(chat_id, "No agent is currently configured for this channel.")
        return {"ok": False, "detail": "no telegram agent configured"}

    await save_message(
        db,
        content=text,
        channel="telegram",
        role="user",
        metadata={
            "chat_id": chat_id,
            "telegram_user": user_info,
            "agent_id": agent_config["id"],
            "update_id": update_id,
        },
    )

    try:
        response_text = await invoke_agent_for_telegram(text, agent_config, chat_id)
    except Exception as exc:
        logger.exception("Telegram agent invocation failed: %s", exc)
        response_text = "Sorry, I encountered an error processing your request."

    await save_message(
        db,
        content=response_text,
        channel="telegram",
        role="assistant",
        metadata={
            "chat_id": chat_id,
            "agent_id": agent_config["id"],
        },
    )

    await send_message(chat_id, response_text)

    return {"ok": True}


@router.post("/set-webhook")
async def register_webhook(payload: dict[str, str]):
    url = payload.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="url is required")
    result = await set_webhook(url)
    return result
