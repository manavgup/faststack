# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

Greenfield build. The legacy cookiecutter template has been removed. All work follows the plan in `docs/design/fastapi-generator-plan.md`. Architecture decisions are tracked in `docs/architecture/adr/`.

## What FastStack Is

A hybrid framework (like Django): thin runtime core (`faststack_core`) that generated projects import at runtime, plus a CLI (`faststack`) that scaffolds projects and entities. NOT a one-shot cookiecutter template.

**Key distinction**: `faststack_core` provides base classes/middleware/logging that users import. The CLI generates business code (models, services, routers) that users own and customize.

## Architecture (Target — v1)

```
faststack/
├── faststack_core/        # Runtime library (pip-installable, users import this)
│   ├── base/              # Entity bases, Repository Protocol, SqlAlchemyRepository, CrudService
│   ├── exceptions/        # DomainError hierarchy + RFC 7807 handlers
│   ├── database/          # Async session config, get_db dependency
│   ├── logging/           # Structured JSON logger, sensitive data masking
│   ├── middleware/        # Correlation ID, request logging, security headers
│   ├── health/            # Health check endpoints
│   ├── settings/          # FastStackConfig dataclass
│   └── setup.py           # One-call setup_app() for all middleware
├── cli/                   # CLI tool (faststack command, built with click)
├── templates/             # Jinja2 templates for code generation
│   ├── project/           # Project scaffold (main.py, pyproject.toml, Docker, Alembic)
│   └── simple/            # Layered architecture entity templates
└── tests/                 # Framework tests (test_core/, test_cli/, test_templates/)
```

## v1 vs v2 Scope

**v1**: Simple (layered) mode only — runtime core, CLI, YAML entities, project scaffolding, entity generation.

**v2 (deferred)**: DDD (onion) mode, auth module, domain events, TypeScript client generation, multi-tenancy.

## Key Design Decisions

- **Async-first** — all repos/services use `AsyncSession`, no sync support
- **Protocol-based repos** — `Repository` Protocol for the contract, `SqlAlchemyRepository` for the implementation, in-memory fakes for testing (no mocks)
- **File ownership** — REGENERATABLE (schemas, fakes, factories) vs PRESERVED (models, repos, services, routers, tests)
- **Model is source of truth** — YAML is input format only; `faststack generate` reads models via AST introspection
- **RFC 7807** for all error responses
- **Lifecycle hooks** (before_create, after_create, etc.) for user customization
- **Composable, not locked** — every component can be disabled or replaced via `FastStackConfig`

## Tech Stack

- Python 3.12+, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, Alembic
- FastAPI native `Depends()` for DI (no dependency-injector)
- Protocol-based repos + in-memory fakes + polyfactory for testing
- ruff + black for linting
- Poetry for package management
- click for CLI

## Common Commands

Run `make` or `make help` for all targets. Key ones:

```bash
make install-dev     # venv + all deps + pre-commit hooks
make check           # lint + typecheck + test with 85% coverage (CI gate)
make test            # pytest with coverage
make test-unit       # core + template tests only
make test-integration # CLI command tests
make lint            # ruff check + black --check
make format          # ruff fix + black
make typecheck       # mypy faststack_core/ cli/
make pre-commit      # run all pre-commit hooks
make clean           # remove caches, build artifacts
```

## Key Documents

- `DEVELOPING.md` — development setup, project structure, how generation works
- `TESTING.md` — test organization, markers, coverage, patterns
- `CONTRIBUTING.md` — workflow, code standards, PR process
- `docs/design/fastapi-generator-plan.md` — design blueprint
- `docs/implementation/v1-implementation-plan.md` — build sequence
- `docs/architecture/adr/` — Architecture Decision Records (the reasoning)
