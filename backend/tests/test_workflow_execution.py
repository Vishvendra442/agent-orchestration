import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_workflow(client: AsyncClient, sample_agent_payload):
    agent1_resp = await client.post("/api/agents/", json={**sample_agent_payload, "name": "Agent A"})
    agent1_id = agent1_resp.json()["id"]

    agent2_resp = await client.post("/api/agents/", json={**sample_agent_payload, "name": "Agent B"})
    agent2_id = agent2_resp.json()["id"]

    import uuid
    node1_id = str(uuid.uuid4())
    node2_id = str(uuid.uuid4())

    workflow_payload = {
        "name": "Test Workflow",
        "description": "A two-agent test workflow",
        "is_template": False,
        "nodes": [
            {"id": node1_id, "agent_id": agent1_id, "node_type": "agent", "label": "Node A"},
            {"id": node2_id, "agent_id": agent2_id, "node_type": "agent", "label": "Node B"},
        ],
        "edges": [
            {"source_node_id": node1_id, "target_node_id": node2_id},
        ],
    }

    resp = await client.post("/api/workflows/", json=workflow_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Workflow"
    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 1


@pytest.mark.asyncio
async def test_list_workflows(client: AsyncClient, sample_agent_payload):
    agent_resp = await client.post("/api/agents/", json=sample_agent_payload)
    agent_id = agent_resp.json()["id"]

    import uuid
    node_id = str(uuid.uuid4())
    workflow_payload = {
        "name": "Listed Workflow",
        "nodes": [{"id": node_id, "agent_id": agent_id, "node_type": "agent", "label": "Node"}],
        "edges": [],
    }
    await client.post("/api/workflows/", json=workflow_payload)

    resp = await client.get("/api/workflows/")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_get_workflow(client: AsyncClient, sample_agent_payload):
    agent_resp = await client.post("/api/agents/", json=sample_agent_payload)
    agent_id = agent_resp.json()["id"]

    import uuid
    node_id = str(uuid.uuid4())
    workflow_payload = {
        "name": "Get Workflow",
        "nodes": [{"id": node_id, "agent_id": agent_id, "node_type": "agent", "label": "N"}],
        "edges": [],
    }
    create_resp = await client.post("/api/workflows/", json=workflow_payload)
    wf_id = create_resp.json()["id"]

    resp = await client.get(f"/api/workflows/{wf_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Get Workflow"


@pytest.mark.asyncio
async def test_delete_workflow(client: AsyncClient, sample_agent_payload):
    agent_resp = await client.post("/api/agents/", json=sample_agent_payload)
    agent_id = agent_resp.json()["id"]

    import uuid
    node_id = str(uuid.uuid4())
    workflow_payload = {
        "name": "Delete Workflow",
        "nodes": [{"id": node_id, "agent_id": agent_id, "node_type": "agent", "label": "N"}],
        "edges": [],
    }
    create_resp = await client.post("/api/workflows/", json=workflow_payload)
    wf_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/workflows/{wf_id}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/workflows/{wf_id}")
    assert resp.status_code == 404
