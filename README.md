<div align="center">
  <h1>strands-dakera</h1>
  <h3>Persistent, decay-weighted memory for Strands Agents</h3>
  <p>
    A community <a href="https://strandsagents.com/">Strands Agents</a> integration backed by a self-hosted
    <a href="https://github.com/dakera-ai/dakera">Dakera</a> memory server.
  </p>
  <p>
    <a href="https://pypi.org/project/strands-dakera/"><img src="https://img.shields.io/pypi/v/strands-dakera.svg" alt="PyPI"></a>
    <a href="https://github.com/dakera-ai/strands-dakera/actions/workflows/ci-python.yml"><img src="https://github.com/dakera-ai/strands-dakera/actions/workflows/ci-python.yml/badge.svg" alt="CI"></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-blue.svg" alt="License"></a>
  </p>
</div>

---

`strands-dakera` gives [Strands](https://github.com/strands-agents/sdk-python) agents a `dakera_memory`
tool for durable memory that survives across sessions. Unlike a fixed-TTL store, Dakera ranks recalled
memories by **importance × recency × semantic relevance**, so the most contextually useful memories
surface first.

- **Decay-weighted recall** — `retrieve` returns at most `top_k` memories ranked by a decay-aware importance signal, not just vector distance.
- **Importance-typed storage** — `store` accepts an `importance` (0.0–1.0), a `memory_type` (episodic / semantic / procedural / working) and, for history written after the fact, the `event_time` the remembered event happened.
- **Agent-loop memory** — `DakeraMemoryStore` plugs into a Strands `MemoryManager`: relevant memories are injected into each model call and new facts are extracted from the conversation, with no explicit tool call.
- **Self-hosted, no cloud key** — runs against your own Dakera server (a single container, or the [`dakera-ai/dakera-deploy`](https://github.com/dakera-ai/dakera-deploy) stack).

## Install

```bash
pip install strands-dakera
```

Requires Python 3.10+ and `strands-agents` 1.45+. Compatible with Dakera server v0.12.0 – v0.12.3
(dakera Python SDK >= 0.14.1); `event_time` needs server v0.12.3 (older servers ignore it).

### Run a Dakera server

A single container is enough to try it out:

```bash
docker run -d --name dakera -p 3000:3000 \
  -e DAKERA_ROOT_API_KEY=dk-mykey \
  ghcr.io/dakera-ai/dakera:0.12.3
curl http://localhost:3000/health
```

For persistent, tiered storage (Dakera + MinIO) use the Docker Compose stack in
[`dakera-ai/dakera-deploy`](https://github.com/dakera-ai/dakera-deploy):

```bash
git clone https://github.com/dakera-ai/dakera-deploy
cd dakera-deploy/docker
cp .env.example .env   # set DAKERA_ROOT_API_KEY (e.g. openssl rand -hex 32) and the MinIO credentials
docker compose up -d   # REST API on http://localhost:3000
```

### Configure

| Variable | Default | Description |
|---|---|---|
| `DAKERA_BASE_URL` | `http://localhost:3000` | Dakera server URL |
| `DAKERA_API_KEY` | _(unset)_ | API key for the Dakera server (the root key above, or a key created with it) |
| `BYPASS_TOOL_CONSENT` | _(unset)_ | `true` suppresses the tool's preview panels before `store` / `update` / `delete` |

```bash
export DAKERA_BASE_URL=http://localhost:3000
export DAKERA_API_KEY=dk-mykey
```

## Usage

### The `dakera_memory` tool

The model calls the tool explicitly. You can also call it yourself through `agent.tool`:

```python
from strands import Agent
from strands_dakera import dakera_memory

agent = Agent(tools=[dakera_memory])

# Store a memory with an importance weight
agent.tool.dakera_memory(
    action="store",
    agent_id="alex",
    content="Alex prefers dark-mode dashboards and async standups.",
    importance=0.8,
    metadata={"category": "preferences"},
)

# Decay-weighted semantic recall: at most top_k ranked memories
agent.tool.dakera_memory(
    action="retrieve",
    agent_id="alex",
    query="how does alex like to work?",
    top_k=5,
)

# Ask the model; it decides when to store or recall
agent("Alex asked for a standup summary. How should I format it for them?")
```

Each call returns a Strands `ToolResult` whose text is the server's JSON answer (`delete`
answers a confirmation line). `retrieve` returns a list of memories with `id`, `content`,
`score` (the server's ranking score, highest first), `importance`, `memory_type`,
`metadata` and `created_at`.

| Action | Required fields | Optional fields | Description |
|---|---|---|---|
| `store` | `agent_id`, `content` | `importance`, `memory_type`, `metadata`, `event_time` | Store a new memory |
| `retrieve` | `agent_id`, `query` | `top_k` (default 5) | Decay-weighted semantic search: at most `top_k` ranked memories |
| `get` | `agent_id`, `memory_id` | — | Fetch a specific memory by ID |
| `update` | `agent_id`, `memory_id` | `content`, `metadata`, `memory_type`, `importance` | Update an existing memory (only the fields given) |
| `delete` | `agent_id`, `memory_id` | — | Delete a memory by ID |

`event_time` is when the remembered event happened, as an RFC 3339 timestamp with an offset
(e.g. `2026-03-01T09:00:00Z`); recency and time filters use it instead of the time of
storage. The `store` result reports content longer than the embedding model reads
(`truncated`, `embedded_tokens`) and request fields the server ignored (`warnings`).

See [`docs/dakera_memory_tool.md`](docs/dakera_memory_tool.md) for the full action reference.

### `DakeraMemoryStore`

`DakeraMemoryStore` is a Strands `MemoryStore`, the `MemoryManager` extension point
(Strands 1.45+). Where the `dakera_memory` tool is called explicitly by the model, a store
plugs into the **agent loop**: the manager searches it before each model call and injects
the relevant memories into the prompt, gives the model a `search_memory` tool, and, when the
store is writable, stores new facts it **extracts** from the conversation.

```python
from strands import Agent
from strands.memory import ExtractionConfig, InvocationTrigger, MemoryManager
from strands_dakera import DakeraMemoryStore

# Recall + write: after every invocation, the agent's model distills facts from the
# conversation and the store writes them to Dakera.
store = DakeraMemoryStore(
    agent_id="alex",
    extraction=ExtractionConfig(trigger=InvocationTrigger()),
)

agent = Agent(memory_manager=MemoryManager(stores=[store]))
agent("Remember that I prefer dark-mode dashboards.")

# A later conversation (a new agent, process or day) recalls it automatically.
agent = Agent(memory_manager=MemoryManager(stores=[store]))
agent("How do I like my dashboards?")
```

`extraction=True` uses the Strands defaults (extraction every 5 invocations). Without
`extraction`, the store is recall-only unless you write to it yourself (`await
store.add(...)`) or enable the manager's add tool (`MemoryManager(stores=[store],
add_tool_config=True)`). `DakeraMemoryStore` implements `search` (decay-weighted recall) and
`add` (a client-side write sink), so extraction uses the manager's client-side
`ModelExtractor`. Each recalled `MemoryEntry` carries the memory's `id`, `score`,
`importance`, `memory_type`, `created_at` and stored metadata in `metadata`.

| Argument | Default | Description |
|---|---|---|
| `agent_id` | _(required)_ | Dakera agent namespace that owns the memories |
| `name` | `"dakera"` | Store identifier, used to target it from memory tools |
| `description` | `"Persistent, decay-weighted long-term memory backed by Dakera."` | Shown in the memory tools' descriptions |
| `writable` | `True` | Whether the manager may write to the store |
| `extraction` | `None` | Automatic extraction (`bool` or `ExtractionConfig`) |
| `max_search_results` | `None` | Result cap per search (unset: the manager's default, 3) |
| `importance` | `None` | Default importance (0.0–1.0) applied to writes |
| `memory_type` | `"episodic"` | Default Dakera memory type for writes |
| `base_url` / `api_key` | env | Override `DAKERA_BASE_URL` / `DAKERA_API_KEY` |

The tool and the store share one server and agent namespace: memories stored with the
tool under `agent_id="alex"` are recalled by `DakeraMemoryStore(agent_id="alex")`.

### Example

[`python/examples/quickstart.py`](python/examples/quickstart.py) runs the tool and the store
against a local server without model credentials:

```bash
cd python
BYPASS_TOOL_CONSENT=true python examples/quickstart.py
```

## Development

The package lives under [`python/`](python/) (monorepo-style layout matching the
[Strands extension-template](https://github.com/strands-agents/extension-template)).

```bash
cd python
pip install hatch
hatch run test        # pytest (no live server required: mocked client)
hatch run prepare     # format + lint + typecheck + test
# Live tests against a real server (e.g. ghcr.io/dakera-ai/dakera:0.12.3):
DAKERA_TEST_URL=http://localhost:3000 DAKERA_API_KEY=dk-mykey hatch run test tests/test_integration.py
```

## Roadmap

- `DakeraSessionManager` — a Strands `SessionManager` that persists conversation state to Dakera as a first-class memory store (tracked separately).

## License

[Apache-2.0](LICENSE). Dakera is a trademark of Dakera. Strands Agents is a project of its respective authors.
