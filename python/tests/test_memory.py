"""
Tests for the dakera_memory tool.
"""

import json
import os
from unittest.mock import MagicMock, create_autospec, patch

import pytest
from dakera import DakeraClient, RecalledMemory, RecallResponse
from strands import Agent
from strands.models.model import Model
from strands.types.tools import AgentTool, ToolUse

from strands_dakera.memory import TOOL_SPEC, DakeraServiceClient, dakera_memory, format_store_response


@pytest.fixture
def mock_tool():
    """Create a mock ToolUse object."""
    mock = MagicMock(spec=ToolUse)
    mock.get.side_effect = lambda key, default=None: {"toolUseId": "test-id", "input": {}}.get(key, default)
    return mock


def make_tool(input_data: dict) -> MagicMock:
    """Helper: build a mock ToolUse with given input dict."""
    mock = MagicMock(spec=ToolUse)
    mock.get.side_effect = lambda key, default=None: {
        "toolUseId": "test-id",
        "input": input_data,
    }.get(key, default)
    return mock


# ---------------------------------------------------------------------------
# DakeraServiceClient init
# ---------------------------------------------------------------------------


def test_service_client_raises_on_missing_package():
    """ImportError when dakera package is not installed."""
    with patch("builtins.__import__", side_effect=ImportError("No module named 'dakera'")):
        with pytest.raises(ImportError, match="dakera package is required"):
            DakeraServiceClient()


@patch.dict(os.environ, {"DAKERA_BASE_URL": "http://localhost:3000", "DAKERA_API_KEY": "dk-test"})
def test_service_client_init():
    """Client initialises from env vars."""
    mock_dakera_client = MagicMock()
    with patch("strands_dakera.memory.DakeraServiceClient.__init__", return_value=None) as patched:
        patched.return_value = None
        client = DakeraServiceClient.__new__(DakeraServiceClient)
        client.client = mock_dakera_client
        assert client.client is mock_dakera_client


# ---------------------------------------------------------------------------
# store action
# ---------------------------------------------------------------------------


@patch.dict(os.environ, {"BYPASS_TOOL_CONSENT": "true"})
def test_store_memory():
    """store action returns success with memory dict."""
    stored = {
        "id": "mem-abc",
        "content": "Test memory content",
        "importance": 0.8,
        "created_at": "2026-07-02T00:00:00Z",
    }

    with patch("strands_dakera.memory.DakeraServiceClient") as MockClient:
        instance = MockClient.return_value
        instance.store_memory.return_value = stored

        tool = make_tool(
            {
                "action": "store",
                "agent_id": "alex",
                "content": "Test memory content",
                "importance": 0.8,
                "metadata": {"category": "notes"},
            }
        )
        result = dakera_memory(tool=tool)

    assert result["status"] == "success"
    body = json.loads(result["content"][0]["text"])
    assert body["id"] == "mem-abc"
    instance.store_memory.assert_called_once_with(
        agent_id="alex",
        content="Test memory content",
        importance=0.8,
        memory_type="episodic",
        metadata={"category": "notes"},
        event_time=None,
    )


def test_store_missing_content():
    """store without content returns error."""
    tool = make_tool({"action": "store", "agent_id": "alex"})
    with patch("strands_dakera.memory.DakeraServiceClient"):
        result = dakera_memory(tool=tool)
    assert result["status"] == "error"
    assert "content is required for store action" in result["content"][0]["text"]


# ---------------------------------------------------------------------------
# retrieve action
# ---------------------------------------------------------------------------


@patch.dict(os.environ, {"BYPASS_TOOL_CONSENT": "true"})
def test_retrieve_memories():
    """retrieve returns a list of matching memories."""
    memories = [
        {"id": "mem-1", "content": "hello world", "score": 0.95, "importance": 0.7},
        {"id": "mem-2", "content": "another fact", "score": 0.80, "importance": 0.5},
    ]
    with patch("strands_dakera.memory.DakeraServiceClient") as MockClient:
        instance = MockClient.return_value
        instance.search_memories.return_value = memories

        tool = make_tool({"action": "retrieve", "agent_id": "alex", "query": "hello", "top_k": 2})
        result = dakera_memory(tool=tool)

    assert result["status"] == "success"
    body = json.loads(result["content"][0]["text"])
    assert len(body) == 2
    assert body[0]["id"] == "mem-1"
    instance.search_memories.assert_called_once_with(agent_id="alex", query="hello", top_k=2)


def test_retrieve_missing_query():
    """retrieve without query returns error."""
    tool = make_tool({"action": "retrieve", "agent_id": "alex"})
    with patch("strands_dakera.memory.DakeraServiceClient"):
        result = dakera_memory(tool=tool)
    assert result["status"] == "error"
    assert "query is required" in result["content"][0]["text"]


def test_retrieve_empty_results():
    """retrieve with no matches returns success with empty list."""
    with patch("strands_dakera.memory.DakeraServiceClient") as MockClient:
        instance = MockClient.return_value
        instance.search_memories.return_value = []

        tool = make_tool({"action": "retrieve", "agent_id": "alex", "query": "xyz"})
        result = dakera_memory(tool=tool)

    assert result["status"] == "success"
    body = json.loads(result["content"][0]["text"])
    assert body == []


# ---------------------------------------------------------------------------
# get action
# ---------------------------------------------------------------------------


def test_get_memory():
    """get returns the memory dict."""
    memory = {
        "id": "mem-abc",
        "content": "stored fact",
        "importance": 0.9,
        "created_at": "2026-07-02T00:00:00Z",
        "metadata": {},
    }
    with patch("strands_dakera.memory.DakeraServiceClient") as MockClient:
        instance = MockClient.return_value
        instance.get_memory.return_value = memory

        tool = make_tool({"action": "get", "agent_id": "alex", "memory_id": "mem-abc"})
        result = dakera_memory(tool=tool)

    assert result["status"] == "success"
    body = json.loads(result["content"][0]["text"])
    assert body["id"] == "mem-abc"
    instance.get_memory.assert_called_once_with("alex", "mem-abc")


def test_get_missing_memory_id():
    """get without memory_id returns error."""
    tool = make_tool({"action": "get", "agent_id": "alex"})
    with patch("strands_dakera.memory.DakeraServiceClient"):
        result = dakera_memory(tool=tool)
    assert result["status"] == "error"
    assert "memory_id is required for get action" in result["content"][0]["text"]


# ---------------------------------------------------------------------------
# update action
# ---------------------------------------------------------------------------


@patch.dict(os.environ, {"BYPASS_TOOL_CONSENT": "true"})
def test_update_memory():
    """update returns updated memory dict."""
    updated = {
        "id": "mem-abc",
        "content": "updated content",
        "importance": 0.9,
        "created_at": "2026-07-02T00:00:00Z",
        "metadata": {"tag": "v2"},
    }
    with patch("strands_dakera.memory.DakeraServiceClient") as MockClient:
        instance = MockClient.return_value
        instance.update_memory.return_value = updated

        tool = make_tool(
            {
                "action": "update",
                "agent_id": "alex",
                "memory_id": "mem-abc",
                "content": "updated content",
                "metadata": {"tag": "v2"},
            }
        )
        result = dakera_memory(tool=tool)

    assert result["status"] == "success"
    body = json.loads(result["content"][0]["text"])
    assert body["content"] == "updated content"
    instance.update_memory.assert_called_once_with(
        agent_id="alex",
        memory_id="mem-abc",
        content="updated content",
        metadata={"tag": "v2"},
        memory_type=None,
        importance=None,
    )


def test_update_missing_memory_id():
    """update without memory_id returns error."""
    tool = make_tool({"action": "update", "agent_id": "alex", "content": "new"})
    with patch("strands_dakera.memory.DakeraServiceClient"):
        result = dakera_memory(tool=tool)
    assert result["status"] == "error"
    assert "memory_id is required for update action" in result["content"][0]["text"]


# ---------------------------------------------------------------------------
# delete action
# ---------------------------------------------------------------------------


@patch.dict(os.environ, {"BYPASS_TOOL_CONSENT": "true"})
def test_delete_memory():
    """delete returns success text with memory_id."""
    with patch("strands_dakera.memory.DakeraServiceClient") as MockClient:
        instance = MockClient.return_value
        instance.delete_memory.return_value = {"status": "ok"}

        tool = make_tool({"action": "delete", "agent_id": "alex", "memory_id": "mem-abc"})
        result = dakera_memory(tool=tool)

    assert result["status"] == "success"
    assert "mem-abc" in result["content"][0]["text"]
    instance.delete_memory.assert_called_once_with("alex", "mem-abc")


def test_delete_missing_memory_id():
    """delete without memory_id returns error."""
    tool = make_tool({"action": "delete", "agent_id": "alex"})
    with patch("strands_dakera.memory.DakeraServiceClient"):
        result = dakera_memory(tool=tool)
    assert result["status"] == "error"
    assert "memory_id is required for delete action" in result["content"][0]["text"]


# ---------------------------------------------------------------------------
# Guard: missing required params
# ---------------------------------------------------------------------------


def test_missing_action():
    """No action returns error."""
    tool = make_tool({"agent_id": "alex"})
    with patch("strands_dakera.memory.DakeraServiceClient"):
        result = dakera_memory(tool=tool)
    assert result["status"] == "error"
    assert "action parameter is required" in result["content"][0]["text"]


def test_missing_agent_id():
    """No agent_id returns error."""
    tool = make_tool({"action": "retrieve", "query": "test"})
    with patch("strands_dakera.memory.DakeraServiceClient"):
        result = dakera_memory(tool=tool)
    assert result["status"] == "error"
    assert "agent_id parameter is required" in result["content"][0]["text"]


def test_invalid_action():
    """Unknown action returns error."""
    tool = make_tool({"action": "explode", "agent_id": "alex"})
    with patch("strands_dakera.memory.DakeraServiceClient"):
        result = dakera_memory(tool=tool)
    assert result["status"] == "error"
    assert "Invalid action" in result["content"][0]["text"]


# ---------------------------------------------------------------------------
# Server v0.12.3 / dakera 0.14.1
# ---------------------------------------------------------------------------


def make_service_client() -> tuple[DakeraServiceClient, MagicMock]:
    """A DakeraServiceClient over a spec'd SDK mock: calls that do not match the SDK signature fail."""
    sdk = create_autospec(DakeraClient, instance=True)
    client = DakeraServiceClient.__new__(DakeraServiceClient)
    client.client = sdk
    return client, sdk


def recalled(memory_id: str, score: float, retrieval: str | None = None) -> RecalledMemory:
    return RecalledMemory(
        id=memory_id,
        content=f"content of {memory_id}",
        memory_type="episodic",
        importance=0.5,
        score=score,
        rank_score=score,
        retrieval=retrieval,
    )


def test_search_asks_for_separate_neighborhood_and_returns_ranked_only():
    """search_memories() requests neighborhood_mode="separate" and drops inline context items."""
    client, sdk = make_service_client()
    sdk.recall.return_value = RecallResponse(
        memories=[recalled("mem-1", 0.9), recalled("mem-2", 0.8), recalled("mem-ctx", 0.0, "neighborhood")]
    )

    results = client.search_memories("alex", "tea", top_k=2)

    sdk.recall.assert_called_once_with(agent_id="alex", query="tea", top_k=2, neighborhood_mode="separate")
    assert [r["id"] for r in results] == ["mem-1", "mem-2"]
    assert results[0]["score"] == 0.9


def test_search_cuts_unmarked_inline_context_from_older_servers():
    """A server up to v0.12.2 ignores neighborhood_mode and appends unmarked context: cut at top_k."""
    client, sdk = make_service_client()
    sdk.recall.return_value = RecallResponse(memories=[recalled("mem-1", 0.9), recalled("mem-2", 0.0)])

    results = client.search_memories("alex", "tea", top_k=1)

    assert [r["id"] for r in results] == ["mem-1"]


def test_search_empty_agent_returns_no_memories():
    """Server v0.12.3 answers a recall of an agent that stored nothing with no memories."""
    client, sdk = make_service_client()
    sdk.recall.return_value = RecallResponse(memories=[])

    assert client.search_memories("new-agent", "anything") == []


def test_service_client_store_forwards_event_time():
    client, sdk = make_service_client()
    sdk.store_memory.return_value = {"id": "mem-1"}

    client.store_memory("alex", "met Sam", importance=0.7, event_time="2026-03-01T09:00:00Z")

    sdk.store_memory.assert_called_once_with(
        agent_id="alex",
        content="met Sam",
        memory_type="episodic",
        importance=0.7,
        metadata=None,
        event_time="2026-03-01T09:00:00Z",
    )


def test_service_client_update_forwards_importance():
    client, sdk = make_service_client()
    sdk.update_memory.return_value = {"id": "mem-1"}

    client.update_memory("alex", "mem-1", importance=0.9)

    sdk.update_memory.assert_called_once_with(
        agent_id="alex",
        memory_id="mem-1",
        content=None,
        metadata=None,
        memory_type=None,
        importance=0.9,
    )


@patch.dict(os.environ, {"BYPASS_TOOL_CONSENT": "true"})
def test_store_action_passes_event_time():
    with patch("strands_dakera.memory.DakeraServiceClient") as MockClient:
        instance = MockClient.return_value
        instance.store_memory.return_value = {"id": "mem-1"}
        tool = make_tool(
            {"action": "store", "agent_id": "alex", "content": "met Sam", "event_time": "2026-03-01T09:00:00Z"}
        )
        result = dakera_memory(tool=tool)

    assert result["status"] == "success"
    assert instance.store_memory.call_args.kwargs["event_time"] == "2026-03-01T09:00:00Z"


@patch.dict(os.environ, {"BYPASS_TOOL_CONSENT": "true"})
def test_update_action_passes_importance():
    with patch("strands_dakera.memory.DakeraServiceClient") as MockClient:
        instance = MockClient.return_value
        instance.update_memory.return_value = {"id": "mem-1"}
        tool = make_tool({"action": "update", "agent_id": "alex", "memory_id": "mem-1", "importance": 0.9})
        result = dakera_memory(tool=tool)

    assert result["status"] == "success"
    assert instance.update_memory.call_args.kwargs["importance"] == 0.9


def test_store_response_reports_truncation_and_warnings():
    panel = format_store_response(
        {
            "id": "mem-1",
            "truncated": True,
            "content_tokens": 900,
            "embedded_tokens": 512,
            "warnings": ["unknown field 'when' ignored"],
        }
    )
    text = str(panel.renderable)
    assert "first 512 of 900 tokens" in text
    assert "unknown field 'when' ignored" in text


# ---------------------------------------------------------------------------
# Registration with a Strands Agent
# ---------------------------------------------------------------------------


class _NoCallModel(Model):
    """A model that must not be called: the tests only use direct tool calls."""

    def update_config(self, **model_config):
        pass

    def get_config(self):
        return {}

    async def structured_output(self, *args, **kwargs):
        raise AssertionError("model called")
        yield  # pragma: no cover

    async def stream(self, *args, **kwargs):
        raise AssertionError("model called")
        yield  # pragma: no cover


def test_dakera_memory_is_an_agent_tool():
    """The exported tool is a Strands AgentTool carrying TOOL_SPEC (a plain function is not registered)."""
    assert isinstance(dakera_memory, AgentTool)
    assert dakera_memory.tool_name == "dakera_memory"
    assert dakera_memory.tool_spec == TOOL_SPEC


@patch.dict(os.environ, {"BYPASS_TOOL_CONSENT": "true"})
def test_agent_registers_and_calls_the_tool():
    """Agent(tools=[dakera_memory]) registers the tool and agent.tool.dakera_memory(...) runs it."""
    agent = Agent(model=_NoCallModel(), tools=[dakera_memory], callback_handler=None)
    assert agent.tool_names == ["dakera_memory"]

    with patch("strands_dakera.memory.DakeraServiceClient") as MockClient:
        instance = MockClient.return_value
        instance.search_memories.return_value = [{"id": "mem-1", "content": "dark mode", "score": 0.9}]
        result = agent.tool.dakera_memory(action="retrieve", agent_id="alex", query="ui preferences", top_k=3)

    assert result["status"] == "success"
    assert json.loads(result["content"][0]["text"])[0]["id"] == "mem-1"
    instance.search_memories.assert_called_once_with(agent_id="alex", query="ui preferences", top_k=3)
