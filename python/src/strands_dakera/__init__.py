"""Strands Dakera — persistent, decay-weighted memory for Strands agents.

Backed by a self-hosted `Dakera <https://github.com/dakera-ai/dakera-deploy>`_
memory server. Exposes the ``dakera_memory`` tool for store / retrieve / get /
update / delete operations with importance-weighted, decay-aware recall.
"""

from strands_dakera.memory import (
    TOOL_SPEC,
    DakeraServiceClient,
    dakera_memory,
)

__all__ = [
    "dakera_memory",
    "DakeraServiceClient",
    "TOOL_SPEC",
]

__version__ = "0.1.0"
