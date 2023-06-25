# FastStack v1 Implementation Plan

## Context

FastStack is a hybrid FastAPI framework (runtime core + CLI generator) replacing a legacy cookiecutter template. The repo is greenfield — only docs exist. We need to build the entire framework across 6 phases (~40 items, ~63 files). All design decisions are captured in `docs/design/fastapi-generator-plan.md` and 7 ADRs in `docs/architecture/adr/`.

**Goal:** A user can `pip install faststack`, run `faststack init my-app`, define entities in YAML, and get a complete async FastAPI project with protocol-based testing, structured logging, and RFC 7807 errors.

---

## Phase 0: Project Bootstrap

Before any code, create the package structure.

### 0.1 Create `pyproject.toml`
- Package: `faststack`, Python `>=3.12`
- Runtime deps: `fastapi`, `sqlalchemy[asyncio]`, `asyncpg`, `pydantic>=2.0`, `alembic`, `click`, `jinja2`, `inflect`, `uvicorn`, `python-json-logger`
- Dev deps: `pytest`, `pytest-asyncio`, `polyfactory`, `ruff`, `black`, `aiosqlite`, `httpx`, `mypy`
- Entry point: `[tool.poetry.scripts] faststack = "cli:cli"`
- Ruff/black/pytest config sections

### 0.2 Create package directories with `__init__.py`
```
faststack_core/{__init__,base/,exceptions/,database/,logging/,middleware/,health/,settings/}
cli/__init__.py
templates/{project/,simple/}
tests/{__init__,test_core/,test_cli/,test_templates/}
```

### 0.3 Create `Makefile`
Common development commands (~15 targets):
```
install          # poetry install
test             # pytest
test-verbose     # pytest -v
test-single      # pytest tests/ -k "$(K)"  (usage: make test-single K=test_name)
lint             # ruff check . && black --check .
format           # ruff check --fix . && black .
typecheck        # mypy faststack_core/ cli/
check            # lint + typecheck + test (CI gate)
clean            # remove __pycache__, .pytest_cache, .coverage, htmlcov, dist, *.egg-info
help             # list all targets with descriptions
```

### 0.4 Root `conftest.py` — pytest-asyncio mode=auto

### 0.5 Verify: `poetry install` succeeds, `make check` passes, `python -c "import faststack_core"` works

---

## Phase 1: Runtime Core

**Depends on:** Phase 0
**Critical files:** `repository.py` (Protocol + SqlAlchemyRepository), `entity.py`, `service.py`

### Parallel track A (no dependencies):
- `faststack_core/base/entity.py` — Entity, AuditedEntity, SoftDeleteEntity, FullAuditedEntity
- `tests/test_core/test_base_entity.py`

### Parallel track B (no dependencies):
- `faststack_core/exceptions/domain.py` — DomainError + 8 subclasses + EXCEPTION_MAP
- `faststack_core/exceptions/handlers.py` — RFC 7807 handler
- `tests/test_core/test_exceptions.py`

### Parallel track C (no dependencies):
- `faststack_core/database/session.py` — DatabaseConfig, async get_db
- `faststack_core/base/permissions.py` — @require_permission, @require_role

### Sequential (depends on A+B+C):
- `faststack_core/base/repository.py` — Repository Protocol[T], SearchableRepository, SqlAlchemyRepository
- `tests/test_core/test_repository.py` — Protocol conformance, async CRUD, soft-delete
- `faststack_core/base/service.py` — CrudService with 6 async lifecycle hooks
- `tests/test_core/test_crud_service.py` — hooks fire, NotFoundError, fake repo in tests

### Verify: `pytest tests/test_core/ -v && ruff check faststack_core/ && black --check faststack_core/`

---

## Phase 2: Logging & Middleware

**Depends on:** Phase 1
**Critical file:** `setup.py` (integrates everything)

### Parallel track A:
- `faststack_core/logging/config.py` — log settings
- `faststack_core/logging/masking.py` — recursive sensitive data masking
- `faststack_core/logging/structured_logger.py` — dual-format (JSON file + colored console)

### Parallel track B:
- `faststack_core/middleware/correlation_id.py` — UUID per request via contextvars
- `faststack_core/middleware/request_logging.py` — method/path/status/duration
- `faststack_core/middleware/security_headers.py` — HSTS, X-Content-Type-Options, etc.

### Parallel track C:
- `faststack_core/health/endpoints.py` — /health + /health/detailed
- `faststack_core/settings/config.py` — FastStackConfig dataclass

### Sequential (depends on all above):
- `faststack_core/setup.py` — `setup_app(app, config)` one-call registration
- Tests: test_logging.py, test_middleware.py, test_health.py, test_setup.py

### Verify: `pytest tests/test_core/ -v` (all Phase 1+2 tests), smoke test with minimal FastAPI app

---

## Phase 3: CLI Foundation + YAML Parser

**Depends on:** Phase 1 (for entity types)
**Critical files:** `model_introspector.py` (HIGHEST RISK), `yaml_parser.py`

### Parallel track A:
- `cli/__init__.py` — Click CLI group with version
- `cli/field_mappings.py` — 13-type YAML → SQLAlchemy → Pydantic map
- `cli/yaml_parser.py` — EntityDefinition/FieldDefinition dataclasses, parse_entities_yaml(), relationship resolution
- `tests/test_cli/test_field_mappings.py`, `tests/test_cli/test_yaml_parser.py`

### Parallel track B:
- `cli/model_introspector.py` — AST-based model reader (parses Mapped[], mapped_column(), relationship())
- `tests/test_cli/test_model_introspector.py` — test with string model files written to temp

**Risk mitigation for introspector:** Only support patterns FastStack generates. Test-driven against known model files.

### Verify: `pytest tests/test_cli/ -v`, cross-check: YAML parse → generate model → introspect model → same EntityDefinition

---

## Phase 4: Project Scaffolding (`faststack init`)

**Depends on:** Phases 1-3

### Parallel (all 8 templates independent):
- `templates/project/pyproject.toml.j2`
- `templates/project/main.py.j2` — imports setup_app, registers entity routers
- `templates/project/config.py.j2` — Pydantic BaseSettings
- `templates/project/Dockerfile.j2`
- `templates/project/docker-compose.yml.j2`
- `templates/project/alembic.ini.j2`
- `templates/project/alembic_env.py.j2` — async engine, auto-model-discovery
- `templates/project/conftest.py.j2` — async fixtures, test DB

### Sequential:
- `cli/cmd_init.py` — `faststack init` command (uses templates + yaml_parser)
- `tests/test_cli/test_init.py` — scaffold to temp dir, verify structure
- `tests/test_templates/test_project_templates.py` — render + ast.parse

### Verify: `faststack init test-project` in temp dir, all generated files parse as valid Python/TOML/YAML

---

## Phase 5: Simple Mode Entity Templates

**Depends on:** Phases 1-4
**Critical file:** `model.py.j2` (must handle all 13 types + 3 relationship types)

### Parallel (all 9 templates independent):
- `templates/simple/model.py.j2` — SQLAlchemy model with enums, relationships, FKs, junction tables
- `templates/simple/schema.py.j2` — Pydantic v2 Create/Update/Response/DetailResponse
- `templates/simple/repository.py.j2` — extends SqlAlchemyRepository
- `templates/simple/service.py.j2` — extends CrudService with hook placeholders
- `templates/simple/router.py.j2` — FastAPI CRUD endpoints, flat routes, query param filtering
- `templates/simple/factory.py.j2` — polyfactory ModelFactory
- `templates/simple/fake_repository.py.j2` — in-memory dict-based, satisfies Protocol
- `templates/simple/test_unit_service.py.j2` — service tests with fake
- `templates/simple/test_integration.py.j2` — API tests with httpx.AsyncClient

### Sequential:
- `tests/test_templates/test_simple_mode.py` — render all 9 for User/Post/Category, verify valid Python, cross-template consistency

### Verify: Render all templates for User entity, `ruff check` + `black --check` on output, fake satisfies Protocol

---

## Phase 6: Entity CLI Commands

**Depends on:** Phases 1-5

### Parallel track A (independent):
- `cli/cmd_migrate.py` — Alembic wrapper (generate/upgrade/downgrade)
- `cli/cmd_list.py` — entity status table with staleness detection
- `tests/test_cli/test_migrate.py`, `tests/test_cli/test_list.py`

### Sequential:
- Registry generation logic (dependencies.py template, router registration in main.py)
- `cli/cmd_add_entity.py` — add-entity (interactive, --fields, --from-yaml, --update)
- `cli/cmd_generate.py` — regenerate REGENERATABLE files from model, skip PRESERVED, hash tracking
- `tests/test_cli/test_add_entity.py`, `tests/test_cli/test_generate.py`

### Verify: Full end-to-end workflow:
```bash
faststack init blog-app --entities fixtures/blog.yaml
cd blog-app
# Verify User + Post + Category generated
# Modify User model (add bio field)
faststack generate User    # schemas updated, service preserved
faststack list             # shows staleness correctly
faststack add-entity Comment --fields "body:text:required,post_id:uuid"
# Verify Comment entity, dependencies.py updated
pytest                     # all generated tests pass
ruff check . && black --check .  # clean output
```

---

## Risk Register

| Risk | Severity | Phase | Mitigation |
|------|----------|-------|------------|
| AST introspection of Mapped[] syntax | **HIGH** | 3 | Test-driven, only support patterns FastStack generates |
| model.py.j2 correctness (13 types x 3 relationships) | **HIGH** | 5 | Test every type+relationship combo with User/Post/Category fixture |
| Protocol[T] + Generic[T] type checker compat | **MEDIUM** | 1 | Add runtime_checkable, test with mypy |
| --update mode AST rewriting | **MEDIUM** | 6 | v1: append fields to class end, not merge. Print diff for review. |
| BaseHTTPMiddleware streaming issues | **LOW** | 2 | Verify Starlette version compat, use raw ASGI if needed |

---

## Key References

- `docs/design/fastapi-generator-plan.md` — all code examples serve as implementation reference
- `docs/architecture/adr/` — 7 ADRs with constraints and alternatives
- Design plan YAML example (User + Post + Category) — golden test fixture for all template testing
