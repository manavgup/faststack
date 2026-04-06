# FastStack

**Hybrid FastAPI framework — runtime core + CLI generator.**

[![CI](https://github.com/manavgup/faststack/actions/workflows/ci.yml/badge.svg)](https://github.com/manavgup/faststack/actions/workflows/ci.yml)
[![Lint](https://github.com/manavgup/faststack/actions/workflows/lint.yml/badge.svg)](https://github.com/manavgup/faststack/actions/workflows/lint.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## What is FastStack?

FastStack scaffolds **production-ready async FastAPI projects** from YAML entity definitions. Define your entities once, get a complete API with models, schemas, repositories, services, routers, dependency injection, and tests — all wired together and ready to run.

Unlike one-shot project generators, FastStack is a **hybrid framework** (like Django):

- **`faststack_core`** — a pip-installable runtime library with base classes, middleware, structured logging, and RFC 7807 error handling that generated projects import
- **`faststack` CLI** — scaffolds projects and entities, regenerates derived files when models change

## Features

- **YAML-driven code generation** — define entities, get 9 files per entity (model, schema, repo, service, router, factory, fakes, unit tests, integration tests)
- **Async-first** — all repos/services use `AsyncSession`, no sync support
- **Protocol-based repositories** — structural typing with in-memory fakes for testing (no mocks)
- **Dependency injection** — auto-generated `dependencies.py` with `Depends()` wiring
- **RFC 7807 errors** — standardized problem-detail error responses
- **Lifecycle hooks** — `before_create`, `after_create`, etc. on every service
- **Structured logging** — JSON + console dual-format, sensitive data masking, correlation IDs
- **Security middleware** — CORS, HSTS, X-Frame-Options, request logging
- **File ownership model** — REGENERATABLE files (schemas, fakes) vs PRESERVED files (models, services) so you can customize without losing changes on regeneration
- **Health checks** — `/health` and `/health/detailed` out of the box
- **Complete test suite** — generated unit tests (fake repos) + integration tests (AsyncClient with DI overrides)

## Quick Start

### Install

```bash
git clone https://github.com/manavgup/faststack.git
cd faststack
make install-dev
```

### Create a Project

Define your entities in YAML:

```yaml
# entities.yaml
entities:
  User:
    base: AuditedEntity
    fields:
      email: {type: string, required: true, unique: true}
      name: {type: string, required: true}
      role: {type: enum, values: [admin, editor, viewer], default: '"viewer"'}
    searchable: [email, name]

  Post:
    base: AuditedEntity
    fields:
      title: {type: string, required: true}
      content: {type: text}
      status: {type: enum, values: [draft, published, archived], default: '"draft"'}
      user_id: {type: uuid, references: User}
    searchable: [title]
```

Scaffold the project:

```bash
poetry run faststack init my-blog --entities entities.yaml
cd my-blog
```

This generates a complete project:

```
my-blog/
├── app/
│   ├── main.py                  # FastAPI app with all routers registered
│   ├── config.py                # Settings from environment variables
│   ├── api/
│   │   ├── dependencies.py      # DI providers (get_db_session, get_*_service)
│   │   └── routes/              # Wired CRUD routers per entity
│   ├── models/                  # SQLAlchemy 2.0 models
│   ├── schemas/                 # Pydantic v2 Create/Update/Response schemas
│   ├── repositories/            # SqlAlchemyRepository subclasses
│   └── services/                # CrudService subclasses with lifecycle hooks
├── tests/
│   ├── unit/                    # Service tests with fake repositories
│   │   └── fakes/               # In-memory repos (Protocol-based)
│   ├── integration/             # API tests with AsyncClient + DI overrides
│   │   └── conftest.py          # Shared client fixture
│   └── factories/               # Polyfactory test data generators
├── alembic/                     # Database migrations
├── pyproject.toml
├── Dockerfile
└── docker-compose.yml
```

### Add More Entities

```bash
# From YAML
poetry run faststack add-entity Comment --from-yaml entities.yaml

# Inline
poetry run faststack add-entity Tag --fields "label:string:required,color:string"

# Check status
poetry run faststack list
```

### Regenerate After Model Changes

Edit a model file, then regenerate derived files (schemas, fakes, factories):

```bash
poetry run faststack generate Post       # Single entity
poetry run faststack generate --all      # All entities
```

Only REGENERATABLE files are overwritten. Your models, services, routers, and tests are preserved.

## Supported Types

| YAML Type | SQLAlchemy | Pydantic | Example |
|-----------|-----------|----------|---------|
| `string` | `String(255)` | `str` | `name: {type: string}` |
| `text` | `Text` | `str` | `bio: {type: text}` |
| `integer` | `Integer` | `int` | `count: {type: integer}` |
| `float` | `Float` | `float` | `score: {type: float}` |
| `boolean` | `Boolean` | `bool` | `active: {type: boolean}` |
| `datetime` | `DateTime` | `datetime` | `expires_at: {type: datetime}` |
| `date` | `Date` | `date` | `born_on: {type: date}` |
| `uuid` | `UUID` | `UUID` | `ref_id: {type: uuid}` |
| `decimal` | `Numeric(10,2)` | `Decimal` | `price: {type: decimal}` |
| `json` | `JSON` | `dict` | `config: {type: json}` |
| `jsonb` | `JSON` | `dict` | `metadata: {type: jsonb}` |
| `enum` | `Enum` | `Literal[...]` | `role: {type: enum, values: [a, b]}` |
| `array` | `ARRAY` | `list` | `tags: {type: array, items: string}` |

Foreign keys: `user_id: {type: uuid, references: User}` with optional `on_delete: cascade|set_null|restrict`.

## Entity Base Classes

| Base | Fields |
|------|--------|
| `Entity` | `id` (UUID primary key) |
| `AuditedEntity` | + `created_at`, `updated_at`, `created_by`, `updated_by` |
| `SoftDeleteEntity` | + `is_deleted`, `deleted_at`, `deleted_by` |
| `FullAuditedEntity` | All of the above |

## Development

```bash
make install-dev    # Full dev setup (venv + deps + pre-commit hooks)
make check          # Lint + typecheck + tests with 85% coverage (CI gate)
make test-unit      # Fast — core + template tests only
make test-e2e       # End-to-end scaffold validation
make format         # Auto-format with ruff + black
make help           # All available targets
```

See [DEVELOPING.md](DEVELOPING.md) for project structure and how code generation works.

## Testing

393 tests at 90% coverage. See [TESTING.md](TESTING.md) for details.

```bash
make test               # All tests + coverage gate
make test-unit          # 175 unit tests
make test-integration   # 162 CLI integration tests
make test-e2e           # 6 end-to-end tests
make coverage           # HTML report → htmlcov/index.html
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for workflow, code standards, and PR process.

## Architecture

- **Design plan:** [`docs/design/fastapi-generator-plan.md`](docs/design/fastapi-generator-plan.md)
- **Implementation plan:** [`docs/implementation/v1-implementation-plan.md`](docs/implementation/v1-implementation-plan.md)
- **Architecture decisions:** [`docs/architecture/adr/`](docs/architecture/adr/)

## License

MIT
