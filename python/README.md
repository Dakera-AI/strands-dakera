# strands-dakera (Python)

Persistent, decay-weighted memory for [Strands Agents](https://github.com/strands-agents/sdk-python),
backed by a self-hosted [Dakera](https://github.com/dakera-ai/dakera-deploy) server.

See the [repository README](../README.md) for full usage. Quick start:

```bash
pip install strands-dakera
```

Compatible with Dakera server v0.12.0 and v0.11.108 (dakera Python SDK >= 0.13.0).

As an explicit tool:

```python
from strands import Agent
from strands_dakera import dakera_memory

agent = Agent(tools=[dakera_memory])
```

Or as a `MemoryStore` that plugs into the agent loop (Strands ≥ 1.45):

```python
from strands import Agent
from strands.memory import MemoryManager
from strands_dakera import DakeraMemoryStore

store = DakeraMemoryStore(agent_id="alex", writable=True, extraction=True)
agent = Agent(memory_manager=MemoryManager(stores=[store]))
```

## Local development

```bash
pip install hatch
hatch run test        # run the test suite (mocked client, no live server)
hatch run lint        # ruff
hatch run typecheck   # mypy
hatch run prepare     # format + lint + typecheck + test
DAKERA_TEST_URL=http://localhost:3000 hatch run test tests/test_integration.py  # live tests against a real server (e.g. ghcr.io/dakera-ai/dakera:0.12.0)
```

## Release

Tag a GitHub release with a `python-v*` tag (e.g. `python-v0.1.0`); the
`publish-python` workflow builds the wheel and publishes it to PyPI via trusted
publishing.
