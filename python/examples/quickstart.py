"""strands-dakera quickstart: the ``dakera_memory`` tool and ``DakeraMemoryStore``.

Runs against a local Dakera server and needs no model credentials: the tool is
called directly (``agent.tool.dakera_memory(...)``) and the store through a
``MemoryManager``, the same paths an agent uses at run time.

    docker run -d --name dakera -p 3000:3000 -e DAKERA_ROOT_API_KEY=dk-mykey \\
        ghcr.io/dakera-ai/dakera:0.12.3
    export DAKERA_BASE_URL=http://localhost:3000 DAKERA_API_KEY=dk-mykey
    BYPASS_TOOL_CONSENT=true python examples/quickstart.py
"""

import asyncio
import json
import time
import uuid
from typing import Any

from strands import Agent
from strands.memory import MemoryManager

from strands_dakera import DakeraMemoryStore, dakera_memory


def tool_result(result: dict) -> Any:
    """The JSON payload of a ``dakera_memory`` tool result (``delete`` answers plain text)."""
    text = result["content"][0]["text"]
    if result["status"] != "success":
        raise RuntimeError(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def tool_demo(agent_id: str) -> None:
    """Store, recall, update and delete through the tool, as a model would."""
    agent = Agent(tools=[dakera_memory], callback_handler=None)

    stored = tool_result(
        agent.tool.dakera_memory(
            action="store",
            agent_id=agent_id,
            content="Alex prefers dark-mode dashboards and async standups.",
            importance=0.8,
            memory_type="semantic",
            metadata={"category": "preferences"},
        )
    )
    tool_result(
        agent.tool.dakera_memory(
            action="store",
            agent_id=agent_id,
            content="Alex moved the team offsite to Lisbon.",
            # When it happened, if not now (RFC 3339; needs server v0.12.3+).
            event_time="2026-03-01T09:00:00Z",
        )
    )
    print(f"stored {stored['id']}")

    # New memories are searchable within about a second.
    memories: list = []
    for _ in range(20):
        memories = tool_result(
            agent.tool.dakera_memory(action="retrieve", agent_id=agent_id, query="how does Alex like to work?", top_k=3)
        )
        if memories:
            break
        time.sleep(0.25)
    for memory in memories:
        print(f"  {memory['score']:.3f}  {memory['content']}")

    updated = tool_result(
        agent.tool.dakera_memory(action="update", agent_id=agent_id, memory_id=stored["id"], importance=0.95)
    )
    print(f"importance of {updated['id']} is now {updated['importance']}")

    print(tool_result(agent.tool.dakera_memory(action="delete", agent_id=agent_id, memory_id=stored["id"])))


async def store_demo(agent_id: str) -> None:
    """Write and recall through a MemoryManager, the agent loop's path."""
    store = DakeraMemoryStore(agent_id=agent_id, importance=0.7)
    manager = MemoryManager(stores=[store])

    await store.add("The user's favourite editor is Helix.", {"source": "quickstart"})

    entries: list = []
    for _ in range(20):
        entries = await manager.search("Which editor does the user use?")
        if entries:
            break
        await asyncio.sleep(0.25)
    for entry in entries:
        print(f"  {entry.content}  {entry.metadata}")


def main() -> None:
    agent_id = f"quickstart-{uuid.uuid4().hex[:8]}"
    print(f"== dakera_memory tool (agent {agent_id})")
    tool_demo(agent_id)
    print("== DakeraMemoryStore via MemoryManager")
    asyncio.run(store_demo(agent_id))


if __name__ == "__main__":
    main()
