import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_agent(client: AsyncClient, sample_agent_payload):
    resp = await client.post("/api/agents/", json=sample_agent_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Agent"
    assert data["role"] == "tester"
    assert data["model"] == "gpt-4o-mini"
    assert data["temperature"] == 0.5
    assert "id" in data


@pytest.mark.asyncio
async def test_list_agents(client: AsyncClient, sample_agent_payload):
    await client.post("/api/agents/", json=sample_agent_payload)
    resp = await client.get("/api/agents/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_get_agent(client: AsyncClient, sample_agent_payload):
    create_resp = await client.post("/api/agents/", json=sample_agent_payload)
    agent_id = create_resp.json()["id"]

    resp = await client.get(f"/api/agents/{agent_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == agent_id
    assert resp.json()["name"] == "Test Agent"


@pytest.mark.asyncio
async def test_update_agent(client: AsyncClient, sample_agent_payload):
    create_resp = await client.post("/api/agents/", json=sample_agent_payload)
    agent_id = create_resp.json()["id"]

    update_payload = {"name": "Updated Agent", "temperature": 0.9}
    resp = await client.put(f"/api/agents/{agent_id}", json=update_payload)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Agent"
    assert resp.json()["temperature"] == 0.9
    assert resp.json()["role"] == "tester"


@pytest.mark.asyncio
async def test_delete_agent(client: AsyncClient, sample_agent_payload):
    create_resp = await client.post("/api/agents/", json=sample_agent_payload)
    agent_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/agents/{agent_id}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/agents/{agent_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_nonexistent_agent(client: AsyncClient):
    resp = await client.get("/api/agents/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_agent_all_fields(client: AsyncClient):
    payload = {
        "name": "Full Config Agent",
        "role": "assistant",
        "system_prompt": "You are configured with all fields.",
        "model": "gpt-4o",
        "tools": ["web_search", "calculator"],
        "channels": ["telegram"],
        "schedule": {"cron": "0 9 * * *"},
        "memory_enabled": True,
        "memory_window": 50,
        "skills": ["research", "math"],
        "interaction_rules": {"max_turns": 10, "allow_handoff": True},
        "guardrails": {"block_profanity": True, "max_output_length": 2000},
        "max_tokens": 8192,
        "temperature": 0.3,
    }
    resp = await client.post("/api/agents/", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["tools"] == ["web_search", "calculator"]
    assert data["channels"] == ["telegram"]
    assert data["schedule"] == {"cron": "0 9 * * *"}
    assert data["guardrails"]["block_profanity"] is True
