# strands-dakera

**Persistent, decay-weighted memory for [Strands Agents](https://strandsagents.com/), powered by a self-hosted [Dakera](https://dakera.ai) server.**

[![CI](https://github.com/Dakera-AI/strands-dakera/actions/workflows/ci-python.yml/badge.svg)](https://github.com/Dakera-AI/strands-dakera/actions/workflows/ci-python.yml)
[![PyPI](https://img.shields.io/pypi/v/strands-dakera)](https://pypi.org/project/strands-dakera/)
[![Downloads](https://img.shields.io/pypi/dm/strands-dakera)](https://pypi.org/project/strands-dakera/)
[![Python](https://img.shields.io/pypi/pyversions/strands-dakera)](https://pypi.org/project/strands-dakera/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](https://github.com/Dakera-AI/strands-dakera/blob/main/LICENSE)
[![Dakera server](https://img.shields.io/badge/Dakera%20server-v0.12.3-D4A843)](https://dakera.ai)
[![LoCoMo](https://img.shields.io/badge/LoCoMo-88.2%25%20Recall%4020-brightgreen)](https://dakera.ai/benchmark)

Give a Strands agent a memory that outlives the process, two ways: a `dakera_memory` tool the
model calls to store and recall, and a `DakeraMemoryStore` that plugs into the agent loop —
relevant memories are injected into every model call and new facts are extracted from the
conversation. Dakera embeds, stores and ranks the memories on the server — no embedding API
key, no vector database in your process — by relevance, importance and recency.

## Why Dakera

- **Native Strands integration points** — an `AgentTool` for `Agent(tools=[...])` and a
  `MemoryStore` for `MemoryManager(stores=[...])`, sharing one server and agent namespace.
- **Memory that survives restarts** — a new agent, process or day with the same `agent_id`
  recalls what earlier conversations stored.
- **Decay-weighted recall** — memories are ranked by importance × recency × semantic
  relevance, not by vector distance alone.
- **No embedding model to run or pay for** — the Dakera server embeds text itself.
- **Self-hosted, one container** — your agents' memories stay on your infrastructure.
- **Measured** — 88.2% Recall@20 on the [LoCoMo long-conversation memory benchmark](https://dakera.ai/benchmark).

## Contents

- [Quick start](#quick-start)
- [Compatibility](#compatibility)
- [What's new in 0.4.0](#whats-new-in-040)
- [`dakera_memory` tool](#dakera_memory-tool)
- [`DakeraMemoryStore`](#dakeramemorystore)
- [`DakeraServiceClient`](#dakeraserviceclient)
- [Configuration](#configuration)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Related packages](#related-packages)
- [Links](#links)
- [License](#license)

## Quick start

**1. Run Dakera**

```bash
docker run -d --name dakera -p 3000:3000 -v dakera-data:/data \
  -e DAKERA_ROOT_API_KEY=dk-mykey \
  ghcr.io/dakera-ai/dakera:0.12.3

curl http://localhost:3000/health   # {"service":"dakera","status":"healthy",...}
```

The image ships its embedding model, so the server is ready in seconds. Docker Compose,
Kubernetes and Helm setups are in [dakera-deploy](https://github.com/Dakera-AI/dakera-deploy).

**2. Install**

```bash
pip install strands-dakera
export DAKERA_BASE_URL=http://localhost:3000 DAKERA_API_KEY=dk-mykey
```

**3. Remember across conversations**

```python
from strands import Agent
from strands.memory import ExtractionConfig, InvocationTrigger, MemoryManager

from strands_dakera import DakeraMemoryStore

# After every invocation the agent's model distills facts from the conversation,
# and the store writes them to Dakera.
store = DakeraMemoryStore(
    agent_id="alex",
    extraction=ExtractionConfig(trigger=InvocationTrigger()),
)

agent = Agent(memory_manager=MemoryManager(stores=[store]))  # Strands' default model
agent("Remember that I prefer dark-mode dashboards.")

# Later — a new agent, process or day — the preference is recalled into the prompt:
agent = Agent(memory_manager=MemoryManager(stores=[store]))
agent("How do I like my dashboards?")
```

Strands' default model is Amazon Bedrock (AWS credentials); pass `Agent(model=...)` for
another provider. No model credentials?
[`examples/quickstart.py`](https://github.com/Dakera-AI/strands-dakera/blob/main/python/examples/quickstart.py)
runs the tool and the store against your server without any.

## Compatibility

| strands-dakera | Dakera server | `dakera` SDK | Strands Agents | Python |
|---|---|---|---|---|
| **0.4.x** | v0.12.0 – **v0.12.3** | ≥ 0.14.1 | `strands-agents` ≥ 1.45 | ≥ 3.10 |
| 0.3.x | v0.11.108, v0.12.0 | ≥ 0.13.1 | `strands-agents` ≥ 1.45 | ≥ 3.10 |

`event_time` needs server v0.12.3; older servers ignore it. `strands-agents` 1.45 is the first
release with the `strands.memory` module that `DakeraMemoryStore` implements.

## What's new in 0.4.0

- **`Agent(tools=[dakera_memory])` works** — `dakera_memory` is now a Strands `AgentTool`
  (before, Strands rejected the plain function and the agent had no memory tool).
- Dakera server **v0.12.3** support with `dakera>=0.14.1`; `retrieve` and
  `DakeraMemoryStore.search()` return at most `top_k` ranked memories, and `score` is the
  server's ranking score.
- `event_time` on `store` — when the remembered event happened, for history written after the
  fact; `importance` on `update`.
- The `store` result flags content longer than the embedding model reads, and request fields
  the server ignored.
- A runnable [`examples/quickstart.py`](https://github.com/Dakera-AI/strands-dakera/blob/main/python/examples/quickstart.py)
  that needs no model credentials.

Full list: [CHANGELOG](https://github.com/Dakera-AI/strands-dakera/blob/main/python/CHANGELOG.md).

## `dakera_memory` tool

A Strands tool the model calls to store, recall, fetch, update and delete memories. You can
also call it yourself through `agent.tool`:

```python
import json

from strands import Agent

from strands_dakera import dakera_memory

agent = Agent(tools=[dakera_memory])

# Store a memory with an importance weight
stored = agent.tool.dakera_memory(
    action="store",
    agent_id="alex",
    content="Alex prefers concise bullet-point answers over long prose.",
    importance=0.85,
    memory_type="semantic",
    metadata={"category": "preferences"},
)
memory_id = json.loads(stored["content"][0]["text"])["id"]

# Store something that happened in the past (server v0.12.3+)
agent.tool.dakera_memory(
    action="store",
    agent_id="alex",
    content="Alex presented the Q1 roadmap to the board.",
    event_time="2026-03-01T09:00:00Z",
)

# Decay-weighted semantic recall: at most top_k ranked memories, most relevant first
agent.tool.dakera_memory(action="retrieve", agent_id="alex", query="communication style", top_k=5)

# Fetch, update (only the fields given change) and delete by id
agent.tool.dakera_memory(action="get", agent_id="alex", memory_id=memory_id)
agent.tool.dakera_memory(
    action="update", agent_id="alex", memory_id=memory_id, importance=0.9,
    content="Alex prefers bullet points and code examples.",
)
agent.tool.dakera_memory(action="delete", agent_id="alex", memory_id=memory_id)
```

In normal use the model calls the tool itself:
`agent("What do you remember about how Alex likes answers?")`.

| Action | Required fields | Optional fields | Description |
|---|---|---|---|
| `store` | `agent_id`, `content` | `importance`, `memory_type`, `metadata`, `event_time` | Store a new memory |
| `retrieve` | `agent_id`, `query` | `top_k` (default 5) | Decay-weighted semantic search: at most `top_k` ranked memories |
| `get` | `agent_id`, `memory_id` | — | Fetch one memory by id |
| `update` | `agent_id`, `memory_id` | `content`, `metadata`, `memory_type`, `importance` | Update an existing memory (only the fields given) |
| `delete` | `agent_id`, `memory_id` | — | Delete a memory |

- `importance` is 0.0–1.0; `memory_type` is `episodic` (default), `semantic`, `procedural` or
  `working`; `event_time` is an RFC 3339 timestamp with an offset (e.g.
  `2026-03-01T09:00:00Z`) that recency and time filters use instead of the time of storage.
- Every action returns a Strands `ToolResult` whose text is the server's JSON answer: the
  memory for `store` / `get` / `update`, a list of memories (`id`, `content`, `score`,
  `importance`, `memory_type`, `metadata`, `created_at`) for `retrieve`, and a confirmation
  line for `delete`. Errors come back as an `"error"` result, not as an exception.
- A `store` on a v0.12.3 server reports `truncated` / `embedded_tokens` when the content is
  longer than the embedding model reads, and `warnings` naming request fields it ignored.
- Before `store`, `update` and `delete` the tool prints a preview panel;
  `BYPASS_TOOL_CONSENT=true` suppresses it.

The full action reference is in
[`docs/dakera_memory_tool.md`](https://github.com/Dakera-AI/strands-dakera/blob/main/docs/dakera_memory_tool.md).

## `DakeraMemoryStore`

A Strands `MemoryStore` — the `MemoryManager` extension point (Strands 1.45+). Where the tool
is called explicitly by the model, the store plugs into the **agent loop**: the manager
searches it before each model call and injects the relevant memories into the prompt, gives
the model a `search_memory` tool, and, when the store is writable, stores the facts it
**extracts** from the conversation (see the [quick start](#quick-start)).

| Argument | Type | Default | Description |
|---|---|---|---|
| `agent_id` | `str` | _(required)_ | Dakera agent namespace that owns the memories |
| `name` | `str` | `"dakera"` | Store identifier, used to target it from memory tools |
| `description` | `str \| None` | `"Persistent, decay-weighted long-term memory backed by Dakera."` | Shown in the memory tools' descriptions |
| `writable` | `bool` | `True` | Whether the manager may write to the store |
| `extraction` | `bool \| ExtractionConfig` | `None` | Automatic extraction; `True` uses the Strands defaults (every 5 invocations) |
| `max_search_results` | `int \| None` | `None` | Result cap per search (unset: the manager's default, 3) |
| `importance` | `float \| None` | `None` | Default importance (0.0–1.0) of writes |
| `memory_type` | `str` | `"episodic"` | Default Dakera memory type of writes |
| `base_url` / `api_key` | `str \| None` | env | Override `DAKERA_BASE_URL` / `DAKERA_API_KEY` |
| `client` | `DakeraServiceClient \| None` | `None` | Use an existing client instead |

Without `extraction` the store is recall-only unless you write to it yourself
(`await store.add(...)`) or enable the manager's add tool
(`MemoryManager(stores=[store], add_tool_config=True)`). Extraction uses the manager's
client-side `ModelExtractor`. Each recalled `MemoryEntry` carries the memory's `id`, `score`,
`importance`, `memory_type`, `created_at` and stored metadata in `metadata`.

The tool and the store share one server and agent namespace: memories stored with the tool
under `agent_id="alex"` are recalled by `DakeraMemoryStore(agent_id="alex")`.

## `DakeraServiceClient`

The thin wrapper over the `dakera` SDK that the tool and the store use, for scripts that work
with the same memories directly.

```python
from strands_dakera import DakeraServiceClient

client = DakeraServiceClient()  # DAKERA_BASE_URL / DAKERA_API_KEY, or base_url= / api_key=
memory = client.store_memory("alex", "Alex works from Lisbon", importance=0.7)
print(client.search_memories("alex", "Where does Alex work?", top_k=3))
client.update_memory("alex", memory["id"], importance=0.9)
client.delete_memory("alex", memory["id"])
```

`store_memory(agent_id, content, importance=None, memory_type="episodic", metadata=None, event_time=None)`,
`get_memory`, `update_memory(..., content=, metadata=, memory_type=, importance=)`,
`search_memories(agent_id, query, top_k=5)` (at most `top_k` ranked memories) and
`delete_memory`.

## Configuration

| Variable | Default | Description |
|---|---|---|
| `DAKERA_BASE_URL` | `http://localhost:3000` | Dakera server URL |
| `DAKERA_API_KEY` | _(unset)_ | API key: the server's `DAKERA_ROOT_API_KEY` or a key created with it |
| `BYPASS_TOOL_CONSENT` | _(unset)_ | `true` suppresses the tool's preview panels before `store` / `update` / `delete` |

`DakeraMemoryStore(base_url=..., api_key=...)` and `DakeraServiceClient(base_url=..., api_key=...)`
override the variables. Keys scoped to namespaces can be created with the root key (see the
[Dakera docs](https://dakera.ai/docs)).

## Examples

| Script | Shows | LLM key? |
|---|---|---|
| [`examples/quickstart.py`](https://github.com/Dakera-AI/strands-dakera/blob/main/python/examples/quickstart.py) | The tool through `Agent`, the store through a `MemoryManager` | No |

```bash
cd python
DAKERA_BASE_URL=http://localhost:3000 DAKERA_API_KEY=dk-mykey BYPASS_TOOL_CONSENT=true \
  python examples/quickstart.py
```

## Troubleshooting

- **`dakera.ConnectionError` / connection refused** — the server is not running or not at
  `DAKERA_BASE_URL`. The docs use port 3000 (`-p 3000:3000`); this repository's CI publishes it
  on 3300. Check with `curl http://localhost:3000/health`.
- **`401` / `AuthenticationError` in an `"error"` tool result** — `DAKERA_API_KEY` does not
  match the server's `DAKERA_ROOT_API_KEY` (or a key created with it).
- **The agent has no `dakera_memory` tool, or `agent.tool.dakera_memory` raises
  `AttributeError`** — strands-dakera before 0.4.0 exported a plain function that Strands
  rejects; upgrade to 0.4.0.
- **The second conversation recalls nothing with `extraction=True`** — the Strands default
  extracts every 5 invocations; use `ExtractionConfig(trigger=InvocationTrigger())` to extract
  after each one, or write with `await store.add(...)`.
- **Nothing recalled for a new agent** — an agent that has stored nothing recalls nothing. A
  server before v0.12.3 answers such a recall with 404 `NAMESPACE_NOT_FOUND` for some queries
  (v0.12.3 answers an empty list); the tool's `retrieve` and `DakeraMemoryStore.search()`
  treat it as no memories, so a new agent starts the same way on every v0.12 server.
- **Fewer results than expected, or `event_time` has no effect** — recall returns at most
  `top_k` ranked memories (a v0.12.3 server's session-neighbourhood context is left out), and
  `event_time` needs server v0.12.3. `GET /health` reports the server version.

## Development

The package lives under `python/` (the layout of the Strands
[extension template](https://github.com/strands-agents/extension-template)).

```bash
cd python
pip install hatch
hatch run prepare     # format + lint + typecheck + test (mocked client, no server)
DAKERA_TEST_URL=http://localhost:3000 DAKERA_API_KEY=dk-mykey hatch run test tests/test_integration.py
```

See [CONTRIBUTING.md](https://github.com/Dakera-AI/strands-dakera/blob/main/CONTRIBUTING.md)
for the live tests, the example and releases.

## Related packages

| Package | What it is |
|---|---|
| [`dakera`](https://pypi.org/project/dakera/) · [`@dakera-ai/dakera`](https://www.npmjs.com/package/@dakera-ai/dakera) · [`dakera-client`](https://crates.io/crates/dakera-client) · [`dakera-go`](https://github.com/Dakera-AI/dakera-go) | Python, TypeScript, Rust and Go SDKs |
| [`langchain-dakera`](https://pypi.org/project/langchain-dakera/) | LangChain (Python): memory, vector store, sessions, knowledge graph |
| [`@dakera-ai/langchain`](https://www.npmjs.com/package/@dakera-ai/langchain) | LangChain.js: memory, vector store, sessions, knowledge graph |
| [`llamaindex-dakera`](https://pypi.org/project/llamaindex-dakera/) | LlamaIndex: memory block, vector store, memory store |
| [`autogen-dakera`](https://pypi.org/project/autogen-dakera/) | AutoGen: `Memory` for `AssistantAgent`, sessions, knowledge graph |
| [`crewai-dakera`](https://pypi.org/project/crewai-dakera/) | CrewAI: storage for a crew's memories |
| **[`strands-dakera`](https://pypi.org/project/strands-dakera/)** | **Strands Agents: memory tool and `MemoryStore`** |
| [`@dakera-ai/ai-sdk`](https://www.npmjs.com/package/@dakera-ai/ai-sdk) | Vercel AI SDK: memory middleware and tools |

## Links

- [dakera.ai](https://dakera.ai) · [Documentation](https://dakera.ai/docs) · [LoCoMo benchmark](https://dakera.ai/benchmark) · [Strands integration guide](https://dakera.ai/integrations/strands.html)
- Self-hosting: [dakera-deploy](https://github.com/Dakera-AI/dakera-deploy) (Docker Compose, Kubernetes) · [dakera-helm](https://github.com/Dakera-AI/dakera-helm) · server image `ghcr.io/dakera-ai/dakera`
- Tools: [dakera-mcp](https://github.com/Dakera-AI/dakera-mcp) (MCP server) · [dakera-cli](https://github.com/Dakera-AI/dakera-cli) (`dk` command line)
- [Issues](https://github.com/Dakera-AI/strands-dakera/issues) · [Changelog](https://github.com/Dakera-AI/strands-dakera/blob/main/python/CHANGELOG.md)

## License

[Apache-2.0](https://github.com/Dakera-AI/strands-dakera/blob/main/LICENSE). Dakera is a
trademark of Dakera. Strands Agents is a project of its respective authors.
