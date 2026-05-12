import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_messages_empty(client: AsyncClient):
    resp = await client.get("/api/messages/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_message_persistence_via_telegram_webhook(client: AsyncClient, sample_agent_payload):
    payload = {**sample_agent_payload, "channels": ["telegram"]}
    await client.post("/api/agents/", json=payload)

    update = {
        "message": {
            "message_id": 1,
            "from": {"id": 12345, "first_name": "Test", "is_bot": False},
            "chat": {"id": 12345, "type": "private"},
            "text": "Hello agent!",
        }
    }

    resp = await client.post("/api/telegram/webhook", json=update)
    assert resp.status_code == 200

    msgs_resp = await client.get("/api/messages/?channel=telegram")
    assert msgs_resp.status_code == 200
    messages = msgs_resp.json()
    assert len(messages) >= 1
    contents = [m["content"] for m in messages]
    assert "Hello agent!" in contents


@pytest.mark.asyncio
async def test_messages_filter_by_channel(client: AsyncClient, sample_agent_payload):
    payload = {**sample_agent_payload, "channels": ["telegram"]}
    await client.post("/api/agents/", json=payload)

    update = {
        "message": {
            "message_id": 2,
            "from": {"id": 99999, "first_name": "User", "is_bot": False},
            "chat": {"id": 99999, "type": "private"},
            "text": "Filter test",
        }
    }
    await client.post("/api/telegram/webhook", json=update)

    resp = await client.get("/api/messages/?channel=internal")
    internal_messages = resp.json()
    telegram_contents = [m["content"] for m in internal_messages]
    assert "Filter test" not in telegram_contents
