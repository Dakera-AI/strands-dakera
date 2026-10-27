# strands-dakera (Python)

Persistent, decay-weighted memory for [Strands Agents](https://github.com/strands-agents/sdk-python),
backed by a self-hosted [Dakera](https://github.com/dakera-ai/dakera) server.

See the [repository README](https://github.com/dakera-ai/strands-dakera#readme) for full usage. Quick start:

```bash
pip install strands-dakera
```

Requires Python 3.10+ and `strands-agents` 1.45+. Compatible with Dakera server v0.12.0 – v0.12.3
(dakera Python SDK >= 0.14.1); `event_time` needs server v0.12.3 (older servers ignore it).

Point it at your server with `DAKERA_BASE_URL` (default `http://localhost:3000`) and
`DAKERA_API_KEY`, e.g. a local one:

```bash
docker run -d --name dakera -p 3000:3000 -e DAKERA_ROOT_API_KEY=dk-mykey ghcr.io/dakera-ai/dakera:0.12.3
export DAKERA_API_KEY=dk-mykey
```

As an explicit tool the model calls (store / retrieve / get / update / delete):

```python
from strands import Agent
from strands_dakera import dakera_memory

agent = Agent(tools=[dakera_memory])
agent.tool.dakera_memory(action="store", agent_id="alex", content="Alex prefers dark-mode dashboards.")
```

Or as a `MemoryStore` that plugs into the agent loop: relevant memories are injected into
each model call, and facts extracted from the conversation are stored:

```python
from strands import Agent
from strands.memory import ExtractionConfig, InvocationTrigger, MemoryManager
from strands_dakera import DakeraMemoryStore

store = DakeraMemoryStore(agent_id="alex", extraction=ExtractionConfig(trigger=InvocationTrigger()))
agent = Agent(memory_manager=MemoryManager(stores=[store]))
```

A runnable example (no model credentials needed) is in
[`examples/quickstart.py`](https://github.com/dakera-ai/strands-dakera/blob/main/python/examples/quickstart.py).

## Local development

```bash
pip install hatch
hatch run test        # run the test suite (mocked client, no live server)
hatch run lint        # ruff
hatch run typecheck   # mypy
hatch run prepare     # format + lint + typecheck + test
# Live tests and the example against a real server (e.g. ghcr.io/dakera-ai/dakera:0.12.3):
DAKERA_TEST_URL=http://localhost:3000 DAKERA_API_KEY=dk-mykey hatch run test tests/test_integration.py
DAKERA_BASE_URL=http://localhost:3000 DAKERA_API_KEY=dk-mykey BYPASS_TOOL_CONSENT=true hatch run python examples/quickstart.py
```

## Release

Tag a GitHub release with a `python-v*` tag (e.g. `python-v0.4.0`); the
`publish-python` workflow builds the wheel and publishes it to PyPI via trusted
publishing. The version comes from the tag; keep `__version__` in
`src/strands_dakera/__init__.py` and `CHANGELOG.md` in step with it.
