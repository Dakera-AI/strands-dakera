"""
Live tests against a real Dakera server (v0.12.0 / v0.11.108).

Skipped unless ``DAKERA_TEST_URL`` is set, e.g.::

    docker run -d -p 3000:3000 -e DAKERA_AUTH_ENABLED=false ghcr.io/dakera-ai/dakera:0.12.0
    DAKERA_TEST_URL=http://localhost:3000 pytest tests/test_integration.py

They exercise every SDK call the tool and the store make, so a removed route or
a changed SDK signature fails here even when the mocked unit tests pass.
"""

import os
import uuid

import pytest

from strands_dakera import DakeraMemoryStore
from strands_dakera.memory import DakeraServiceClient

TEST_URL = os.environ.get("DAKERA_TEST_URL")

pytestmark = pytest.mark.skipif(not TEST_URL, reason="DAKERA_TEST_URL not set (no live Dakera server)")


@pytest.fixture
def client() -> DakeraServiceClient:
    return DakeraServiceClient(base_url=TEST_URL, api_key=os.environ.get("DAKERA_API_KEY"))


@pytest.fixture
def agent_id() -> str:
    return f"strands-it-{uuid.uuid4().hex[:12]}"


def test_service_client_round_trip(client, agent_id):
    """store -> get -> update -> recall -> delete against the server."""
    stored = client.store_memory(
        agent_id,
        "Alex prefers green tea in the morning",
        importance=0.8,
        memory_type="semantic",
        metadata={"source": "integration"},
    )
    memory_id = stored.get("memory_id") or stored.get("id")
    assert memory_id

    got = client.get_memory(agent_id, memory_id)
    assert "green tea" in got["content"]

    client.update_memory(agent_id, memory_id, content="Alex prefers jasmine tea in the morning")
    assert "jasmine tea" in client.get_memory(agent_id, memory_id)["content"]

    results = client.search_memories(agent_id, "what tea does Alex drink", top_k=5)
    assert any(r["id"] == memory_id for r in results)

    client.delete_memory(agent_id, memory_id)
    results = client.search_memories(agent_id, "what tea does Alex drink", top_k=5)
    assert all(r["id"] != memory_id for r in results)


async def test_memory_store_add_and_search(client, agent_id):
    """DakeraMemoryStore writes and reads through the same server."""
    store = DakeraMemoryStore(agent_id=agent_id, client=client)
    stored = await store.add("The deployment window is Friday at 18:00 UTC", {"topic": "ops"})
    assert stored.get("memory_id") or stored.get("id")

    entries = await store.search("when is the deployment window")
    assert entries
    assert any("Friday" in e.content for e in entries)
