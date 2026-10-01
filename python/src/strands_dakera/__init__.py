"""Strands Dakera — persistent, decay-weighted memory for Strands agents.

Backed by a self-hosted `Dakera <https://github.com/dakera-ai/dakera-deploy>`_
memory server. Two integration points, sharing one server:

- :func:`dakera_memory` — a tool the model calls explicitly for store / retrieve
  / get / update / delete operations.
- :class:`DakeraMemoryStore` — a ``MemoryStore`` that plugs into the agent loop
  via a ``MemoryManager``, with automatic memory injection and extraction.

Both offer importance-weighted, decay-aware recall.
"""

from strands_dakera.memory import (
    TOOL_SPEC,
    DakeraServiceClient,
    dakera_memory,
)
from strands_dakera.store import (
    DakeraMemoryStore,
    DakeraMemoryStoreConfig,
)

__all__ = [
    "dakera_memory",
    "DakeraServiceClient",
    "DakeraMemoryStore",
    "DakeraMemoryStoreConfig",
    "TOOL_SPEC",
]

__version__ = "0.3.0"
