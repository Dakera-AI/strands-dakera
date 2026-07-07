"""
Tests for the DakeraMemoryStore (Strands MemoryStore integration).

The store is exercised with a mocked DakeraServiceClient, so no live Dakera
server (or the `dakera` SDK) is required.
"""

from unittest.mock import MagicMock

import pytest
from strands.memory import MemoryEntry, MemoryStore
from strands.memory.types import _has_method, _has_write_sink

from strands_dakera import DakeraMemoryStore


@pytest.fixture
def mock_client():
    """A mocked DakeraServiceClient."""
    return MagicMock()


def make_store(mock_client, **kwargs):
    """Build a store wired to the mocked client."""
    return DakeraMemoryStore(agent_id="alex", client=mock_client, **kwargs)


# ---------------------------------------------------------------------------
# Construction / protocol conformance
# ---------------------------------------------------------------------------


def test_requires_agent_id():
    """agent_id is mandatory."""
    with pytest.raises(ValueError, match="agent_id is required"):
        DakeraMemoryStore(agent_id="")


def test_is_a_memory_store(mock_client):
    """The store is a genuine MemoryStore subclass (MemoryStore is a
    non-runtime-checkable Protocol, so check the MRO rather than isinstance)."""
    store = make_store(mock_client)
    assert MemoryStore in type(store).__mro__


def test_protocol_attributes_default(mock_client):
    """Protocol attributes take sensible, writable-by-default values."""
    store = make_store(mock_client)
    assert store.name == "dakera"
    assert store.description is not None
    assert store.max_search_results is None
    assert store.writable is True
    assert store.extraction is None
    assert store.agent_id == "alex"


def test_protocol_attributes_override(mock_client):
    """Config fields are honored."""
    store = make_store(
        mock_client,
        name="notes",
        description="d",
        max_search_results=3,
        writable=False,
        extraction=True,
        importance=0.9,
        memory_type="semantic",
    )
    assert store.name == "notes"
    assert store.max_search_results == 3
    assert store.writable is False
    assert store.extraction is True
    assert store.importance == 0.9
    assert store.memory_type == "semantic"


def test_write_sink_detection(mock_client):
    """`add` is a real write sink; `add_messages` is only the inherited stub."""
    store = make_store(mock_client)
    assert _has_method(store, "search") is True
    assert _has_method(store, "add") is True
    assert _has_method(store, "add_messages") is False
    assert _has_method(store, "initialize") is False
    assert _has_method(store, "get_tools") is False
    assert _has_write_sink(store) is True


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


async def test_search_maps_to_memory_entries(mock_client):
    """Dakera hits are mapped to MemoryEntry with metadata preserved."""
    mock_client.search_memories.return_value = [
        {
            "id": "mem-1",
            "content": "Alex prefers dark roast",
            "score": 0.91,
            "importance": 0.8,
            "memory_type": "semantic",
            "created_at": "2026-07-02T00:00:00Z",
            "metadata": {"category": "prefs"},
        }
    ]
    store = make_store(mock_client)

    results = await store.search("coffee")

    assert len(results) == 1
    entry = results[0]
    assert isinstance(entry, MemoryEntry)
    assert entry.content == "Alex prefers dark roast"
    assert entry.metadata["id"] == "mem-1"
    assert entry.metadata["score"] == 0.91
    assert entry.metadata["category"] == "prefs"


async def test_search_default_top_k(mock_client):
    """With no options and no configured max, the default top_k is used."""
    mock_client.search_memories.return_value = []
    store = make_store(mock_client)

    await store.search("q")

    mock_client.search_memories.assert_called_once_with("alex", "q", 5)


async def test_search_options_override_top_k(mock_client):
    """SearchOptions.max_search_results wins over the configured default."""
    mock_client.search_memories.return_value = []
    store = make_store(mock_client, max_search_results=3)

    await store.search("q", {"max_search_results": 10})

    mock_client.search_memories.assert_called_once_with("alex", "q", 10)


async def test_search_config_top_k(mock_client):
    """The configured max is used when options omit it."""
    mock_client.search_memories.return_value = []
    store = make_store(mock_client, max_search_results=7)

    await store.search("q")

    mock_client.search_memories.assert_called_once_with("alex", "q", 7)


async def test_search_handles_missing_content(mock_client):
    """A hit without content maps to an empty string, not None."""
    mock_client.search_memories.return_value = [{"id": "mem-2"}]
    store = make_store(mock_client)

    results = await store.search("q")

    assert results[0].content == ""
    assert results[0].metadata == {"id": "mem-2"}


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------


async def test_add_writes_to_dakera(mock_client):
    """add() forwards agent_id, content, importance, memory_type and metadata."""
    stored = {"id": "mem-9", "content": "new fact"}
    mock_client.store_memory.return_value = stored
    store = make_store(mock_client, importance=0.6, memory_type="semantic")

    result = await store.add("new fact", {"source": "chat"})

    assert result == stored
    mock_client.store_memory.assert_called_once_with("alex", "new fact", 0.6, "semantic", {"source": "chat"})


# ---------------------------------------------------------------------------
# lazy client construction
# ---------------------------------------------------------------------------


def test_client_constructed_lazily(monkeypatch):
    """No DakeraServiceClient is built until the client property is accessed."""
    calls = {"n": 0}

    class FakeClient:
        def __init__(self, base_url=None, api_key=None):
            calls["n"] += 1
            self.base_url = base_url
            self.api_key = api_key

    monkeypatch.setattr("strands_dakera.store.DakeraServiceClient", FakeClient)

    store = DakeraMemoryStore(agent_id="alex", base_url="http://h:3000", api_key="dk-x")
    assert calls["n"] == 0  # not built yet

    client = store.client
    assert calls["n"] == 1
    assert client.base_url == "http://h:3000"
    assert client.api_key == "dk-x"

    # Second access reuses the same instance.
    assert store.client is client
    assert calls["n"] == 1
