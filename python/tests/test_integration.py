"""
Live tests against a real Dakera server (v0.12.3; the round trips also pass on v0.12.0).

Skipped unless ``DAKERA_TEST_URL`` is set, e.g.::

    docker run -d -p 3000:3000 -e DAKERA_AUTH_ENABLED=false ghcr.io/dakera-ai/dakera:0.12.3
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


def test_search_of_empty_agent_returns_nothing(client, agent_id):
    """v0.12.3 answers a recall of an agent that stored nothing with no memories (was a 404)."""
    assert client.search_memories(agent_id, "anything at all", top_k=3) == []


def test_search_returns_at_most_top_k_with_session_neighbourhood(client, agent_id):
    """Memories stored in one session get neighbourhood context; it must not push results past top_k."""
    session = client.client.start_session(agent_id)
    for i in range(6):
        client.client.store_memory(agent_id, f"Alex tried tea variety number {i} today", session_id=session["id"])

    results = client.search_memories(agent_id, "which tea did Alex try", top_k=2)

    assert len(results) == 2
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_store_event_time_and_update_importance(client, agent_id):
    """event_time is recorded as _dakera_event_time; update_memory() changes the importance."""
    stored = client.store_memory(agent_id, "Alex met Sam at the conference", event_time="2026-03-01T09:00:00Z")
    memory_id = stored.get("memory_id") or stored.get("id")
    assert memory_id

    got = client.get_memory(agent_id, memory_id)
    assert got["metadata"]["_dakera_event_time"] == 1772355600

    client.update_memory(agent_id, memory_id, importance=0.95)
    assert client.get_memory(agent_id, memory_id)["importance"] == pytest.approx(0.95)
