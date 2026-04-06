# Developing FastStack

This guide gets you from zero to a working development environment.

## Prerequisites

- **Python 3.12+**
- **Poetry** — `pipx install poetry`
- **Git**

## Quick Start

```bash
git clone https://github.com/manavgup/faststack.git
cd faststack
make install-dev
make check
```

`make install-dev` creates a virtual environment, installs all dependencies, and sets up pre-commit hooks. `make check` runs lint + typecheck + tests with coverage — the same gate that CI runs.

## Project Structure

```
faststack/
├── faststack_core/          # Runtime library (users import this)
│   ├── base/                # Entity bases, Repository Protocol, CrudService
│   ├── exceptions/          # DomainError hierarchy + RFC 7807 handlers
│   ├── database/            # Async session config, get_db dependency
│   ├── logging/             # Structured JSON logger, sensitive data masking
│   ├── middleware/          # Correlation ID, request logging, security headers
│   ├── health/              # Health check endpoints
│   ├── settings/            # FastStackConfig dataclass
│   └── setup.py             # One-call setup_app() for all middleware
├── cli/                     # CLI tool (faststack command, built with Click)
│   ├── cmd_init.py          # faststack init
│   ├── cmd_add_entity.py    # faststack add-entity
│   ├── cmd_generate.py      # faststack generate
│   ├── cmd_list.py          # faststack list
│   ├── cmd_migrate.py       # faststack migrate
│   ├── yaml_parser.py       # YAML entity definitions → EntityDefinition
│   ├── model_introspector.py # AST-based SQLAlchemy model reader
│   └── field_mappings.py    # YAML ↔ SQLAlchemy ↔ Pydantic type mappings
├── templates/               # Jinja2 templates for code generation
│   ├── project/             # Project scaffold (8 templates)
│   └── simple/              # Entity templates (11 templates)
├── tests/                   # Framework tests
│   ├── test_core/           # Runtime library tests (unit)
│   ├── test_cli/            # CLI command tests (integration)
│   ├── test_templates/      # Template rendering tests (unit)
│   └── test_e2e/            # End-to-end scaffold validation
├── examples/                # Example YAML files + smoke tests
└── docs/                    # Design docs, ADRs, implementation plan
```

## Make Targets

Run `make` or `make help` to see all available targets, organized by category:

- **🌱 Installation** — `venv`, `install`, `install-dev`, `update`
- **🧪 Testing** — `test`, `test-unit`, `test-integration`, `test-e2e`, `coverage`
- **🔍 Quality** — `lint`, `format`, `typecheck`, `check`, `pre-commit`
- **🧹 Cleanup** — `clean`, `clean-all`

## How Code Generation Works

FastStack generates projects from YAML entity definitions. The pipeline:

```
entities.yaml → yaml_parser.py → EntityDefinition → Jinja2 templates → .py files
```

1. **YAML parsing** (`cli/yaml_parser.py`) — reads entity fields, resolves FK relationships
2. **Template rendering** (`templates/simple/*.j2`) — generates 9 files per entity:
   - `model.py` — SQLAlchemy ORM model
   - `schema.py` — Pydantic Create/Update/Response schemas
   - `repository.py` — SqlAlchemyRepository subclass
   - `service.py` — CrudService subclass with lifecycle hooks
   - `router.py` — FastAPI router with CRUD endpoints + Depends() wiring
   - `factory.py` — Polyfactory test data factory
   - `fake_repository.py` — In-memory repository for unit tests
   - `test_unit_service.py` — Service unit tests
   - `test_integration.py` — API integration tests
3. **Registry files** (multi-entity) — generated after all entities:
   - `dependencies.py` — DI providers for all entities
   - `tests/integration/conftest.py` — AsyncClient fixture with fake repo overrides

### File Ownership

Templates are classified as **REGENERATABLE** or **PRESERVED**:

| REGENERATABLE (safe to overwrite) | PRESERVED (user owns) |
|---|---|
| schemas, fakes, factories | models, repos, services, routers, tests |
| `dependencies.py`, integration conftest | — |

`faststack generate` only overwrites REGENERATABLE files. Use `--force` for PRESERVED files.

### Model Introspection

`faststack generate` reads existing SQLAlchemy models via AST parsing (`cli/model_introspector.py`), extracts an `EntityDefinition`, and regenerates derived files. The model is the source of truth — not YAML.

## CLI Commands

```bash
faststack init <project> [--entities entities.yaml]   # Scaffold project
faststack add-entity <Name> --fields "name:string:required"  # Add entity
faststack add-entity <Name> --from-yaml entities.yaml  # Add from YAML
faststack generate <Name>                              # Regenerate derived files
faststack generate --all                               # Regenerate all entities
faststack list                                         # Show entity status
faststack migrate generate "message"                   # Create Alembic migration
faststack migrate upgrade                              # Apply migrations
faststack migrate downgrade                            # Rollback one migration
```

## Key Design Decisions

See `docs/architecture/adr/` for full rationale. Summary:

- **Async-first** — no sync support (ADR-001)
- **Protocol-based repos** — structural typing, in-memory fakes for tests (ADR-002)
- **YAML input, model source of truth** — AST introspection for regeneration (ADR-003)
- **RFC 7807 errors** — standardized error responses (ADR-004)
- **Lifecycle hooks** — `before_create`, `after_create`, etc. (ADR-005)
- **File ownership** — REGENERATABLE vs PRESERVED (ADR-006)
- **v1 = simple mode only** — DDD deferred to v2 (ADR-007)
