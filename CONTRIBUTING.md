# Contributing to strands-dakera

Thanks for helping improve the Dakera integration for Strands Agents.

## Reporting bugs and suggesting features

Open an issue at <https://github.com/Dakera-AI/strands-dakera/issues> with your Python,
`strands-agents`, `strands-dakera` and Dakera server versions (`curl http://localhost:3000/health`
reports the server version), what you did, and the error or traceback. Do not report security
vulnerabilities in public issues: use a private
[security advisory](https://github.com/Dakera-AI/strands-dakera/security/advisories/new).

## Development setup

The package lives under `python/` (the layout of the Strands extension template). Python 3.10+
and [hatch](https://hatch.pypa.io/):

```bash
cd python
pip install hatch
hatch run test        # pytest: unit tests against a mocked client, no server needed
hatch run lint        # ruff
hatch run typecheck   # mypy
hatch run prepare     # format + lint + typecheck + test
```

CI also checks formatting with `hatch run ruff format --check src tests examples`.

Unit tests mock the `dakera` SDK client with a spec, so a call that does not match the SDK's
signature fails the test. New behaviour needs a unit test and, when it calls the server, a live
test in `tests/test_integration.py`.

## Live tests and the example

`tests/test_integration.py` runs every SDK call the tool and `DakeraMemoryStore` make against a
real server; it is skipped unless `DAKERA_TEST_URL` is set. Start the server version CI uses:

```bash
docker run -d --name dakera -p 3000:3000 -e DAKERA_ROOT_API_KEY=dk-mykey \
  ghcr.io/dakera-ai/dakera:0.12.3
curl http://localhost:3000/health

cd python
DAKERA_TEST_URL=http://localhost:3000 DAKERA_API_KEY=dk-mykey hatch run test tests/test_integration.py
DAKERA_BASE_URL=http://localhost:3000 DAKERA_API_KEY=dk-mykey BYPASS_TOOL_CONSENT=true \
  hatch run python examples/quickstart.py
```

## Pull requests

1. Branch from `main`, make the change with tests, and run `hatch run prepare`.
2. Update `python/CHANGELOG.md` and, when the public API or behaviour changes, both READMEs
   (`README.md` and `python/README.md` — PyPI shows the latter; keep them identical and use
   absolute links).
3. Open a pull request against `main` describing what changed and how you tested it.

## Releases

Tag a GitHub release with a `python-v*` tag (e.g. `python-v0.4.0`); the `publish-python`
workflow builds the wheel and publishes it to PyPI via trusted publishing. The version comes
from the tag; keep `__version__` in `python/src/strands_dakera/__init__.py` and
`python/CHANGELOG.md` in step with it.
