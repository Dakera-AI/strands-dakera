# Dakera Memory Tool

The `dakera_memory` tool provides persistent, decay-weighted agent memory for Strands agents, backed by a self-hosted [Dakera](https://dakera.ai) memory server.

Unlike key-value stores, Dakera ranks recalled memories by **importance**, **recency**, and **semantic relevance**, so the most useful context surfaces first.

## Prerequisites

### 1. Run a Dakera server

A single container (Dakera server v0.12.0 – v0.12.3; `event_time` needs v0.12.3):

```bash
docker run -d --name dakera -p 3000:3000 \
  -e DAKERA_ROOT_API_KEY=dk-mykey \
  ghcr.io/dakera-ai/dakera:0.12.3
```

Or, for persistent tiered storage, the Docker Compose stack (Dakera API server + MinIO) from [`dakera-ai/dakera-deploy`](https://github.com/dakera-ai/dakera-deploy):

```bash
git clone https://github.com/dakera-ai/dakera-deploy
cd dakera-deploy/docker
cp .env.example .env   # set DAKERA_ROOT_API_KEY and the MinIO credentials
docker compose up -d
```

Either way the REST API listens on **port 3000**.

### 2. Install the package

```bash
pip install strands-dakera
```

### 3. Configure environment variables

| Variable | Default | Description |
|---|---|---|
| `DAKERA_BASE_URL` | `http://localhost:3000` | Dakera server URL |
| `DAKERA_API_KEY` | _(none)_ | API key, if authentication is enabled (it is by default) |
| `BYPASS_TOOL_CONSENT` | _(none)_ | `true` suppresses the preview panels before mutative actions |

## Usage

```python
from strands import Agent
from strands_dakera import dakera_memory

agent = Agent(tools=[dakera_memory])

# Store a memory with importance weighting
stored = agent.tool.dakera_memory(
    action="store",
    agent_id="alex",
    content="Alex prefers concise bullet-point answers over long prose.",
    importance=0.85,
    memory_type="semantic",
    metadata={"category": "preferences"},
)

# Store something that happened in the past (server v0.12.3+)
agent.tool.dakera_memory(
    action="store",
    agent_id="alex",
    content="Alex presented the Q1 roadmap to the board.",
    event_time="2026-03-01T09:00:00Z",
)

# Semantic recall: decay-weighted, at most top_k memories, most relevant first
agent.tool.dakera_memory(
    action="retrieve",
    agent_id="alex",
    query="user communication style",
    top_k=5,
)

# The memory id is in the store result (a JSON memory object)
import json

memory_id = json.loads(stored["content"][0]["text"])["id"]

# Fetch a specific memory by ID
agent.tool.dakera_memory(action="get", agent_id="alex", memory_id=memory_id)

# Update a memory's content and importance
agent.tool.dakera_memory(
    action="update",
    agent_id="alex",
    memory_id=memory_id,
    content="Alex prefers bullet points and code examples.",
    importance=0.9,
)

# Delete a memory
agent.tool.dakera_memory(action="delete", agent_id="alex", memory_id=memory_id)
```

In normal use the model calls the tool itself: `agent("What do you remember about how Alex likes answers?")`.

## Actions

| Action | Required params | Optional params | Description |
|---|---|---|---|
| `store` | `agent_id`, `content` | `importance`, `memory_type`, `metadata`, `event_time` | Store a new memory |
| `retrieve` | `agent_id`, `query` | `top_k` (default 5) | Decay-weighted semantic search: at most `top_k` ranked memories |
| `get` | `agent_id`, `memory_id` | — | Fetch one memory by ID |
| `update` | `agent_id`, `memory_id` | `content`, `metadata`, `memory_type`, `importance` | Update an existing memory (only the fields given change) |
| `delete` | `agent_id`, `memory_id` | — | Remove a memory |

### Results

Every action returns a Strands `ToolResult` (`status` `"success"` or `"error"`). Its text is the server's JSON answer:

- `store`, `get`, `update`: the memory (`id`, `content`, `importance`, `memory_type`, `metadata`, `created_at`, ...). A `store` on a v0.12.3 server also reports `truncated` / `content_tokens` / `embedded_tokens` when the content is longer than the embedding model reads (only the first `embedded_tokens` are searchable), and `warnings` naming request fields the server ignored.
- `retrieve`: a list of memories with `id`, `content`, `score` (the server's ranking score, highest first), `importance`, `memory_type`, `metadata` and `created_at`. Session context the server can add next to the ranked results is left out, so the list never exceeds `top_k`.
- `delete`: a confirmation line.

Errors (an unknown memory id, a server that cannot be reached, a missing field) come back as an `"error"` result with the message, not as an exception.

### Memory types

| Type | Use case |
|---|---|
| `episodic` | Specific events or interactions (default) |
| `semantic` | Facts, preferences, general knowledge |
| `procedural` | Workflows and how-to knowledge |
| `working` | Short-lived context for the current session |

### Importance scoring

`importance` is a float from `0.0` to `1.0`. Higher values make a memory decay more slowly and more likely to surface in recall:

- `0.9–1.0` — critical facts (e.g. user identity, strong preferences)
- `0.7–0.8` — important but routine (e.g. frequently-used configs)
- `0.4–0.6` — background context

### Event time

`event_time` is when the remembered event happened, as an RFC 3339 timestamp with an offset (e.g. `2026-03-01T09:00:00Z`). Use it when writing history after the fact: a Dakera server v0.12.3+ uses it for recency and time filters, while `created_at` stays the time of storage. Older servers ignore it.

## Preview panels

Before a mutative action (`store`, `update`, `delete`) the tool prints a preview panel of what it is about to change; after each action it prints the result. Set `BYPASS_TOOL_CONSENT=true` to suppress the previews in automated or test environments.

## Tests

From the `python/` directory:

```bash
pip install hatch
hatch run test   # unit tests, no server needed (mocked Dakera client)

# Live tests against a real server
DAKERA_TEST_URL=http://localhost:3000 DAKERA_API_KEY=dk-mykey hatch run test tests/test_integration.py -v
```
