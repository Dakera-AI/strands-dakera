<div align="center">
  <h1>strands-dakera</h1>
  <h3>Persistent, decay-weighted memory for Strands Agents</h3>
  <p>
    A community <a href="https://strandsagents.com/">Strands Agents</a> integration backed by a self-hosted
    <a href="https://github.com/dakera-ai/dakera-deploy">Dakera</a> memory server.
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

- **Decay-weighted recall** — `retrieve` returns memories ranked by a decay-aware importance signal, not just vector distance.
- **Importance-typed storage** — `store` accepts an `importance` (0.0–1.0) and a `memory_type` (episodic / semantic / procedural / working).
- **Self-hosted, no cloud key** — runs against a local [`dakera-ai/dakera-deploy`](https://github.com/dakera-ai/dakera-deploy) docker-compose stack (server + MinIO, port 3000).

## Install

```bash
pip install strands-dakera
```

Run a Dakera server (once):

```bash
git clone https://github.com/dakera-ai/dakera-deploy && cd dakera-deploy && docker compose up -d
```

Configure via environment variables:

| Variable | Default | Description |
|---|---|---|
| `DAKERA_BASE_URL` | `http://localhost:3000` | Dakera server URL |
| `DAKERA_API_KEY` | _(unset)_ | API key for the Dakera server (`dk-...`) |

## Usage

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

# Decay-weighted semantic recall
agent.tool.dakera_memory(
    action="retrieve",
    agent_id="alex",
    query="how does alex like to work?",
    top_k=5,
)
```

### Actions

| Action | Required fields | Description |
|---|---|---|
| `store` | `agent_id`, `content` | Store a new memory (`importance`, `memory_type`, `metadata` optional) |
| `retrieve` | `agent_id`, `query` | Decay-weighted semantic search (`top_k` optional, default 5) |
| `get` | `agent_id`, `memory_id` | Fetch a specific memory by ID |
| `update` | `agent_id`, `memory_id` | Update content / metadata of an existing memory |
| `delete` | `agent_id`, `memory_id` | Delete a memory by ID |

Mutative actions (`store`, `update`, `delete`) prompt for confirmation unless `BYPASS_TOOL_CONSENT=true`.

See [`docs/dakera_memory_tool.md`](docs/dakera_memory_tool.md) for the full action reference.

## Memory store

`DakeraMemoryStore` is a Strands [`MemoryStore`](https://strandsagents.com/) — a
`MemoryManager` extension point (Strands ≥ 1.45). Where the `dakera_memory` tool is
called explicitly by the model, a store plugs into the **agent loop** directly: the
manager searches it to recall context (injected into the prompt automatically) and,
when writable, writes new memories — either directly or via periodic **extraction**
from the conversation. Both share one Dakera server and agent namespace.

```python
from strands import Agent
from strands.memory import MemoryManager
from strands_dakera import DakeraMemoryStore

# Recall + write, distilling facts from the conversation every few turns.
store = DakeraMemoryStore(agent_id="alex", writable=True, extraction=True)
agent = Agent(memory_manager=MemoryManager(stores=[store]))

# The agent now recalls from and writes to Dakera without any explicit tool call.
agent("Remember that I prefer dark-mode dashboards.")
agent("How do I like my dashboards?")  # recalls the stored preference
```

`DakeraMemoryStore` implements `search` (decay-weighted recall) and `add` (a client-side
write sink), so enabling `extraction` uses the manager's client-side `ModelExtractor` to
distill facts before storing them.

| Argument | Default | Description |
|---|---|---|
| `agent_id` | _(required)_ | Dakera agent namespace that owns the memories |
| `name` | `"dakera"` | Store identifier, used to target it from memory tools |
| `writable` | `True` | Whether the manager may write to the store |
| `extraction` | `None` | Automatic extraction (`bool` or `ExtractionConfig`) |
| `max_search_results` | `None` | Default result cap per search (falls back to 5) |
| `importance` | `None` | Default importance (0.0–1.0) applied to writes |
| `memory_type` | `"episodic"` | Default Dakera memory type for writes |
| `base_url` / `api_key` | env | Override `DAKERA_BASE_URL` / `DAKERA_API_KEY` |

## Development

The package lives under [`python/`](python/) (monorepo-style layout matching the
[Strands extension-template](https://github.com/strands-agents/extension-template)).

```bash
cd python
pip install hatch
hatch run test        # pytest (no live server required — mocked client)
hatch run prepare     # format + lint + typecheck + test
```

## Roadmap

- `DakeraSessionManager` — a Strands `SessionManager` that persists conversation state to Dakera as a first-class memory store (tracked separately).

## License

[Apache-2.0](LICENSE). Dakera is a trademark of Dakera. Strands Agents is a project of its respective authors.
