# Changelog

All notable changes to the `strands-dakera` Python package. Versions come from the
`python-vX.Y.Z` release tags.

## [0.4.0] - 2026-10-27

Dakera server **v0.12.3** support. Compatible with Dakera server v0.12.0 – v0.12.3;
`event_time` needs v0.12.3 (older servers ignore it).

### Changed

- Requires `dakera>=0.14.1` (the Python SDK release for server v0.12.3; it keeps working with
  v0.12.0 – v0.12.2). The SDK no longer repeats a `store_memory()` that failed with a `5xx` or
  a dropped connection (only `429` / `503` and failed connects are retried for writes), so a
  store through the tool or `DakeraMemoryStore.add()` is sent at most once on such errors.
- `__version__` is `0.4.0`.

### Fixed

- `retrieve` (tool) and `DakeraMemoryStore.search()` returned more than `top_k` /
  `max_search_results` memories on a v0.12.3 server: it appends session-neighbourhood context
  after the ranked results by default (e.g. 3 results for `top_k=2`). Recall now asks for
  that context separately (`neighborhood_mode="separate"`) and returns only the ranked
  results, cut at `top_k` (older servers append the context unmarked). `score` is the
  server's ranking score (`rank_score` on v0.12.3), non-increasing over the results.

### Added

- `event_time` on the tool's `store` action and `DakeraServiceClient.store_memory()`: when
  the remembered event happened (RFC 3339; the client also takes Unix seconds). The server
  uses it for recency and time filters; `created_at` stays the time of storage.
- `importance` on the tool's `update` action and `DakeraServiceClient.update_memory()`.
- The `store` result panel flags a memory whose content was longer than the embedding model
  reads (`truncated`, only the first `embedded_tokens` are searchable) and lists the
  server's `warnings` (request fields it ignored); both are in the returned JSON too.
- Unit tests against a spec'd `DakeraClient` mock (calls that do not match the SDK signature
  fail), and live tests for v0.12.3: recall of an agent that stored nothing returns no
  memories (older servers answered `404`), at most `top_k` results with session
  neighbourhood, `event_time` and importance updates.
- CI: an integration job runs `tests/test_integration.py` against
  `ghcr.io/dakera-ai/dakera:0.12.3`, polling `/health` from the runner (the image ships no
  `curl` for an in-container health check).

## [0.3.0] - 2026-10-01

Dakera server **v0.12.0** support. Compatible with Dakera server v0.12.0 and v0.11.108.

### Changed

- Requires `dakera>=0.13.1` (the Python SDK release for server v0.12.0; it also works
  with v0.11.108). The SDK calls this package makes (`store_memory`, `get_memory`,
  `update_memory`, `recall`, `forget`) keep their signatures, so no API change here.
  0.13.1 is the minimum because `update_memory()` in dakera 0.13.0 sent no `agent_id`,
  which the server requires, so every update through `DakeraServiceClient` failed with a 400. SDK errors are now typed (`ServiceUnavailableError`, `PayloadTooLargeError`,
  `FeatureNotAvailableError`, `ConflictError`, all `DakeraError`s); the `dakera_memory`
  tool still reports them as an error result.
- `__version__` is `0.3.0`.

### Added

- `tests/test_integration.py`: live tests against a real server (skipped unless
  `DAKERA_TEST_URL` is set) covering every SDK call the tool and `DakeraMemoryStore` make.

## [0.2.0] - 2026-07-07

### Added

- `DakeraMemoryStore`, a Strands `MemoryStore` backed by Dakera.

## [0.1.0] - 2026-07-02

### Added

- `dakera_memory` tool: store / retrieve / get / update / delete agent memories.
