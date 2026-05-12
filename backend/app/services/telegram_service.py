import logging
from typing import Optional

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

TELEGRAM_API = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"


async def set_webhook(url: str):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{TELEGRAM_API}/setWebhook",
            json={"url": url},
        )
        data = resp.json()
        if data.get("ok"):
            logger.info("Telegram webhook set: %s", url)
        else:
            logger.error("Failed to set Telegram webhook: %s", data)
        return data


async def send_message(chat_id: int | str, text: str, parse_mode: str = "Markdown"):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
            },
            timeout=10,
        )
        return resp.json()


async def invoke_agent_for_telegram(
    text: str,
    agent_config: dict,
    chat_id: int | str,
) -> str:
    llm = ChatOpenAI(
        model=agent_config.get("model", settings.OPENAI_MODEL),
        api_key=settings.OPENAI_API_KEY,
        max_tokens=agent_config.get("max_tokens", 4096),
        temperature=agent_config.get("temperature", 0.7),
    )

    tools_list = agent_config.get("tools", [])
    if tools_list:
        from app.runtime.tools.registry import get_tools
        tools = get_tools(tools_list)
        llm = llm.bind_tools(tools)

    system_prompt = agent_config.get("system_prompt", "You are a helpful assistant.")
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=text),
    ]

    response = await llm.ainvoke(messages)
    return response.content


async def get_telegram_agent_config(db) -> Optional[dict]:
    from sqlalchemy import select
    from app.models.agent import Agent

    result = await db.execute(select(Agent))
    agents = result.scalars().all()
    for agent in agents:
        channels = agent.channels or []
        if "telegram" in channels:
            return {
                "id": str(agent.id),
                "name": agent.name,
                "system_prompt": agent.system_prompt,
                "model": agent.model,
                "tools": agent.tools or [],
                "max_tokens": agent.max_tokens,
                "temperature": agent.temperature,
                "guardrails": agent.guardrails or {},
            }
    return None
