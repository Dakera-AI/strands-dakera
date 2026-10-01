# Changelog

All notable changes to the `strands-dakera` Python package. Versions come from the
`python-vX.Y.Z` release tags.

## [0.3.0] - 2026-10-01

Dakera server **v0.12.0** support. Compatible with Dakera server v0.12.0 and v0.11.108.

### Changed

- Requires `dakera>=0.13.0` (the Python SDK release for server v0.12.0; it also works
  with v0.11.108). The SDK calls this package makes (`store_memory`, `get_memory`,
  `update_memory`, `recall`, `forget`) keep their signatures in 0.13.0, so no API change
  here. SDK errors are now typed (`ServiceUnavailableError`, `PayloadTooLargeError`,
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
