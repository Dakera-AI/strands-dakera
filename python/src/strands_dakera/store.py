"""A Strands ``MemoryStore`` backed by a self-hosted Dakera memory server.

A memory store gives a Strands agent cross-session recall: a
:class:`~strands.memory.MemoryManager` searches it to recall facts and, when
writable, writes new ones — either directly or via automatic extraction from the
conversation. Unlike the ``dakera_memory`` tool (which the model calls
explicitly), a store plugs into the agent loop out of the box, with memory
injection and extraction triggers handled by the manager.

The store wraps the same Dakera REST API used by the ``dakera_memory`` tool
(via :class:`~strands_dakera.memory.DakeraServiceClient`), so a store and the
tool can share one server and one agent namespace.

Example:
    ```python
    from strands import Agent
    from strands.memory import MemoryManager
    from strands_dakera import DakeraMemoryStore

    # Recall + write, with automatic extraction every few turns.
    store = DakeraMemoryStore(agent_id="alex", writable=True, extraction=True)
    agent = Agent(memory_manager=MemoryManager(stores=[store]))
    ```

Configure the server via the ``base_url`` / ``api_key`` arguments, or the
``DAKERA_BASE_URL`` (default ``http://localhost:3000``) and ``DAKERA_API_KEY``
environment variables. See https://github.com/dakera-ai/dakera-deploy.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from strands.memory import MemoryEntry, MemoryStore, MemoryStoreConfig, SearchOptions

from strands_dakera.memory import DakeraServiceClient

logger = logging.getLogger(__name__)

DEFAULT_MAX_SEARCH_RESULTS = 5
DEFAULT_MEMORY_TYPE = "episodic"


class DakeraMemoryStoreConfig(MemoryStoreConfig, total=False):
    """Configuration for a :class:`DakeraMemoryStore`.

    Extends the base :class:`~strands.memory.MemoryStoreConfig` (``name``,
    ``description``, ``max_search_results``, ``writable``, ``extraction``) with
    Dakera-specific fields.

    Attributes:
        agent_id: Dakera agent namespace that owns the memories. Required.
        importance: Default importance (0.0-1.0) applied to writes.
        memory_type: Default Dakera memory type for writes
            (``episodic`` | ``semantic`` | ``procedural`` | ``working``).
        base_url: Dakera server URL. Defaults to ``$DAKERA_BASE_URL`` or
            ``http://localhost:3000``.
        api_key: Dakera API key. Defaults to ``$DAKERA_API_KEY``.
    """

    agent_id: str
    importance: float
    memory_type: str
    base_url: str
    api_key: str


class DakeraMemoryStore(MemoryStore):
    """A Strands :class:`~strands.memory.MemoryStore` backed by Dakera.

    Implements :meth:`search` (decay-weighted semantic recall) and :meth:`add`
    (a single write sink). Because it implements ``add`` (client-side write)
    rather than ``add_messages``, enabling ``extraction`` uses the manager's
    client-side :class:`~strands.memory.extraction.model_extractor.ModelExtractor`
    to distill facts from the conversation before they are stored.
    """

    def __init__(
        self,
        agent_id: str,
        *,
        name: str = "dakera",
        description: str | None = "Persistent, decay-weighted long-term memory backed by Dakera.",
        max_search_results: int | None = None,
        writable: bool = True,
        extraction: Any = None,
        importance: float | None = None,
        memory_type: str = DEFAULT_MEMORY_TYPE,
        base_url: str | None = None,
        api_key: str | None = None,
        client: DakeraServiceClient | None = None,
    ) -> None:
        """Initialize the store.

        Args:
            agent_id: Dakera agent namespace that owns the memories. Required.
            name: Unique store identifier, used to target it in tools.
            description: Human-readable description, included in tool descriptions.
            max_search_results: Default maximum results per search.
            writable: Whether the store accepts writes.
            extraction: Automatic-extraction config (``bool | ExtractionConfig``).
            importance: Default importance (0.0-1.0) applied to writes.
            memory_type: Default Dakera memory type for writes.
            base_url: Dakera server URL (defaults to ``$DAKERA_BASE_URL``).
            api_key: Dakera API key (defaults to ``$DAKERA_API_KEY``).
            client: Pre-built :class:`DakeraServiceClient` (mainly for testing);
                when omitted, one is constructed lazily on first use.
        """
        if not agent_id:
            raise ValueError("agent_id is required for DakeraMemoryStore")

        # MemoryStore Protocol attributes.
        self.name = name
        self.description = description
        self.max_search_results = max_search_results
        self.writable = writable
        self.extraction = extraction

        # Dakera-specific configuration.
        self.agent_id = agent_id
        self.importance = importance
        self.memory_type = memory_type

        self._base_url = base_url
        self._api_key = api_key
        self._client = client

    @property
    def client(self) -> DakeraServiceClient:
        """The Dakera client, constructed lazily on first use."""
        if self._client is None:
            self._client = DakeraServiceClient(base_url=self._base_url, api_key=self._api_key)
        return self._client

    async def search(self, query: str, options: SearchOptions | None = None) -> list[MemoryEntry]:
        """Search Dakera for entries matching ``query``, ordered by relevance.

        Uses Dakera's decay-weighted, access-aware recall, so results favor
        important, recently used memories.
        """
        top_k = options.get("max_search_results") if options is not None else None
        if top_k is None:
            top_k = self.max_search_results
        if top_k is None:
            top_k = DEFAULT_MAX_SEARCH_RESULTS

        memories = await asyncio.to_thread(self.client.search_memories, self.agent_id, query, top_k)
        return [self._to_entry(m) for m in memories]

    async def add(self, content: str, metadata: dict[str, Any] | None = None) -> Any:
        """Write a single memory to Dakera.

        Extraction writes are at-least-once, so this tolerates duplicate content;
        Dakera de-duplicates on the server. The resolved value is the stored
        memory dict returned by the server.
        """
        return await asyncio.to_thread(
            self.client.store_memory,
            self.agent_id,
            content,
            self.importance,
            self.memory_type,
            metadata,
        )

    @staticmethod
    def _to_entry(memory: dict[str, Any]) -> MemoryEntry:
        """Map a Dakera memory dict to a Strands :class:`~strands.memory.MemoryEntry`."""
        content = memory.get("content") or ""
        metadata: dict[str, Any] = {}
        for key in ("id", "score", "importance", "memory_type", "created_at"):
            value = memory.get(key)
            if value is not None:
                metadata[key] = value
        extra = memory.get("metadata")
        if isinstance(extra, dict):
            metadata.update(extra)
        return MemoryEntry(content=content, metadata=metadata or None)
