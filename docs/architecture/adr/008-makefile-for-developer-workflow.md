# ADR-008: Makefile for Developer Workflow

- *Status:* Accepted
- *Date:* 2026-03-30
- *Deciders:* Manav
- *Related:* [ADR-007](007-v1-scope-boundary.md)

## Context

Developers working on FastStack need to run a variety of commands: install dependencies, run tests, lint code, type-check, format, and clean artifacts. Each tool has its own invocation syntax and flags:

- `poetry install`
- `pytest -v --cov=faststack_core`
- `ruff check . && black --check .`
- `mypy faststack_core/ cli/`

Without a single entry point, every contributor must memorize these commands or look them up. This creates friction — especially for new contributors and AI coding assistants.

The mcp-context-forge project uses a comprehensive Makefile (500+ targets covering Kubernetes, Helm, Rust, load testing). That level of complexity is inappropriate for FastStack v1, but the principle of a self-documenting command interface is sound.

## Decision

**A lean Makefile (~15 targets) as the single entry point for all development commands.**

Targets:
- `make install` — `poetry install`
- `make test` — `pytest`
- `make test-verbose` — `pytest -v`
- `make test-single K=test_name` — `pytest -k "$(K)"`
- `make lint` — `ruff check . && black --check .`
- `make format` — `ruff check --fix . && black .`
- `make typecheck` — `mypy faststack_core/ cli/`
- `make check` — `lint + typecheck + test` (CI gate, single command)
- `make clean` — remove `__pycache__`, `.pytest_cache`, `.coverage`, `htmlcov`, `dist`, `*.egg-info`
- `make help` — list all targets with descriptions (default target)

New targets are added as the project grows (e.g., `make docs`, `make dist` in v2), but the Makefile stays lean — no target without regular use.

## Consequences

### Positive
- One command to verify everything works: `make check`
- Self-documenting: `make help` lists all available commands
- Consistent across environments — no "works on my machine" flag differences
- AI coding assistants (Claude Code, Codex) can discover commands via `make help`
- New contributors productive immediately without reading build docs

### Negative
- Requires `make` installed (standard on macOS/Linux, needs setup on Windows)
- Another file to maintain — though a ~50 line Makefile is trivial

### Neutral
- Does not replace Poetry — the Makefile calls Poetry/pytest/ruff under the hood
- Generated projects (from `faststack init`) get their own Makefile with similar targets

## Alternatives Considered

| Option | Why Not |
|--------|---------|
| Just use Poetry scripts (`poetry run pytest`) | Verbose, no composition (`make check` = 3 commands in one). No `help` target. |
| Task runner (invoke, nox, tox) | Adds a dependency. Makefile is zero-dependency (built into every Unix system). Over-engineered for ~15 targets. |
| Shell scripts (`scripts/test.sh`, etc.) | The legacy cookiecutter template used this approach. Harder to discover, no `help` target, fragmented across files. |
| No task runner — just document commands in README | People don't read READMEs before running commands. `make help` is faster. |

## References

- [IBM/mcp-context-forge Makefile](https://github.com/IBM/mcp-context-forge/blob/main/Makefile) — inspiration for the approach (adapted to ~15 targets from 500+)
