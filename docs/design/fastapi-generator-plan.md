# FastStack — Hybrid FastAPI Framework + CLI Generator

## Context

We're building a **hybrid framework** (like Django's model: thin runtime core + CLI scaffolding) for generating production-ready FastAPI projects. This is NOT a one-shot cookiecutter template — it's a pip-installable framework that generated projects depend on at runtime.

### What Makes This Different From Existing Tools

| Existing Tool | Gap We Fill |
|---------------|-------------|
| fastapi/full-stack-fastapi-template | No service layer, no repo abstraction, routes hit DB directly, single `models.py` |
| FastForge | Sync-only, no repo abstraction (concrete SQLAlchemy), no test story at all, ORM IS the domain model |
| dddpy | Single aggregate only, no cross-aggregate patterns, no generator, ABC over Protocol, no tests |
| greeden.me blog | Blog post only — no runnable code, no CLI, no generator |

### Our Differentiators
1. **Async-first** — every layer uses `AsyncSession`, unlike all reference projects (sync-only or unaddressed)
2. **Protocol-based repository** — structural typing for testability, in-memory fakes over mocks
3. **Multi-entity scaffolding from YAML** — define all entities with fields and relationships upfront
4. **CLI `add-entity` command** — scaffold new entities after project creation
5. **Thin runtime core** — base classes, exceptions, logging, middleware (user imports but owns business code)
6. **Complete CRUD + tests generated per entity** — fakes, factories, unit tests, integration tests
7. **Lifecycle hooks** — `before_create`, `after_create`, etc. for customization without subclassing

### Reference Architectures
- **Simple mode**: Modeled after [rag_modulo](https://github.com/manavgup/rag_modulo/tree/main/backend/rag_solution) — Model/Schema/Repo/Service/Router with domain exceptions
- **DDD mode** (v2): Modeled after [dddpy](https://github.com/iktakahiro/dddpy) — Onion architecture with Value Objects, Use Cases, DTO mapping, domain layer isolation
- **Testing pattern**: From [greeden.me blog](https://blog.greeden.me/en/2025/12/23/practical-fastapi-x-clean-architecture-guide/) — Protocol-based repos with in-memory fakes
- **Framework features**: Inspired by [FastForge](https://github.com/Datacrata/fastforge) — base entities, lifecycle hooks, CLI generation
- **Production logging & observability**: From [mcp-context-forge](https://github.com/IBM/mcp-context-forge) — structured JSON logging, correlation IDs, request logging with masking, health checks

### Reference Project Research Summary

| Concern | FastForge | dddpy | FastAPI Template | Greeden.me |
|---|---|---|---|---|
| Domain/infra separation | None (ORM IS the model) | Excellent (DTO bridge) | None (SQLModel dual-use) | Partial (Protocol boundary) |
| Testability | No test story | Architecturally testable but no tests | Requires real DB | In-memory fakes — best |
| Repo abstraction | Concrete SQLAlchemy | ABC interface | No abstraction | Protocol — most Pythonic |
| Async support | Sync only | Sync only | Sync only | Not addressed |
| Multi-entity | CLI generates per-entity | Single aggregate only | Single models.py | Single example |

**The gap none of them fill** — and what FastStack delivers: Protocol-based testing with fakes, async-first repositories, lifecycle hooks for customization, CLI entity generation, and structured logging — all in one cohesive framework.

---

## Architecture Overview

```
faststack/                          # The pip-installable package
├── faststack_core/                           # Runtime library (users import this)
│   ├── base/
│   │   ├── entity.py                   # Entity, AuditedEntity, SoftDeleteEntity, FullAuditedEntity
│   │   ├── repository.py              # Repository Protocol + SqlAlchemyRepository
│   │   ├── service.py                 # CrudService with lifecycle hooks (before_create, after_create, etc.)
│   │   └── permissions.py             # @require_permission, @require_role decorators
│   ├── exceptions/
│   │   ├── domain.py                  # DomainError hierarchy (NotFound, AlreadyExists, Validation, etc.)
│   │   └── handlers.py               # RFC 7807 global exception handlers
│   ├── database/
│   │   ├── session.py               # DatabaseConfig, async get_db dependency
│   │   └── alembic_utils.py        # Migration helpers
│   ├── logging/
│   │   ├── structured_logger.py     # StructuredLogger: JSON to files, text to console
│   │   ├── masking.py               # SensitiveDataMasker: recursive pattern-based masking
│   │   └── config.py               # Log settings: level, format, rotation, destinations
│   ├── middleware/
│   │   ├── correlation_id.py        # CorrelationIdMiddleware: UUID per request in all logs
│   │   ├── request_logging.py       # RequestLoggingMiddleware: method/path/status/duration
│   │   └── security_headers.py      # SecurityHeadersMiddleware: HSTS, X-Content-Type, etc.
│   ├── health/
│   │   └── endpoints.py             # /health (simple) + /health/detailed (DB, version)
│   ├── settings/
│   │   └── config.py                # FastStackConfig dataclass for setup_app()
│   └── setup.py                     # setup_app(): registers all middleware, handlers, health
│
├── cli/                               # CLI tool (faststack command)
│   ├── __init__.py                    # Main CLI dispatcher
│   ├── cmd_init.py                    # Scaffold new project
│   ├── cmd_add_entity.py             # Add entity to existing project
│   ├── cmd_generate.py               # Regenerate schemas/fakes from models
│   ├── cmd_migrate.py                # Alembic migration wrapper
│   ├── cmd_list.py                   # Show entities and generation status
│   ├── yaml_parser.py               # entities.yaml parser + type mapping
│   ├── model_introspector.py         # AST-based model reader (for regeneration)
│   └── field_mappings.py            # YAML type → SQLAlchemy → Pydantic mapping
│
├── templates/                         # Jinja2 templates for code generation
│   ├── project/                       # Project scaffold templates
│   │   ├── pyproject.toml.j2
│   │   ├── Dockerfile.j2
│   │   ├── docker-compose.yml.j2
│   │   ├── alembic.ini.j2
│   │   ├── alembic_env.py.j2         # Async env.py with auto-model-discovery
│   │   ├── main.py.j2
│   │   ├── config.py.j2
│   │   └── conftest.py.j2
│   └── simple/                        # Layered architecture entity templates
│       ├── model.py.j2
│       ├── schema.py.j2
│       ├── repository.py.j2
│       ├── service.py.j2
│       ├── router.py.j2
│       ├── factory.py.j2
│       ├── fake_repository.py.j2
│       ├── test_unit_service.py.j2
│       └── test_integration.py.j2
│
├── tests/                             # Tests for the framework itself
│   ├── test_core/
│   ├── test_cli/
│   └── test_templates/
├── pyproject.toml                     # Package config (installs faststack_core + faststack CLI)
└── README.md
```

---

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Async | Async-first, no sync | FastAPI's value prop is async. SQLAlchemy 2.0 `AsyncSession` is mature. Supporting both doubles surface area. All reference projects are sync-only — we differentiate. |
| ORM | SQLAlchemy 2.0 | Industry standard, async support, massive ecosystem |
| Database | PostgreSQL | Production standard. JSONB, arrays, enums all PostgreSQL features. |
| Migrations | Alembic (wrapped by CLI) | Industry standard, auto-detection from models, async `env.py` |
| Pydantic | v2 | Current, faster, `model_validate()`, `ConfigDict` |
| DI | FastAPI native `Depends()` | No extra library, easy test overrides |
| Repo abstraction | Protocol (structural typing) | Fakes satisfy the contract without inheritance. More Pythonic than ABC. Enables in-memory testing. |
| Testing | In-memory fakes + polyfactory | Fakes test real behavior (not scripted responses). Faster than mocks, more reliable. |
| Linting | ruff + black | Consistent, fast |
| Package manager | Poetry | Per original requirements |
| Entity input | Custom YAML (v1) | Simple, covers relationships and custom types |
| Exceptions | Domain hierarchy + RFC 7807 | Industry standard structured error responses |
| Architecture | Simple (layered) in v1, DDD (onion) in v2 | Ship the simpler mode first, battle-test it, then tackle DDD |

---

## What Lives in the Framework vs What Gets Generated

| In the framework (import from `faststack_core`) | Generated into user's project (they own it) |
|--------------------------------------------|---------------------------------------------|
| `FullAuditedEntity`, `SoftDeleteEntity` base classes | Their entity models inheriting from base |
| `Repository` Protocol + `SqlAlchemyRepository` | Custom repository methods and queries [PRESERVED] |
| `CrudService` with lifecycle hooks | Their service with custom business logic in hooks [PRESERVED] |
| `DomainError` hierarchy + RFC 7807 handlers | Entity-specific exception subclasses |
| `DatabaseConfig`, async `get_db` | Their database URL and connection settings |
| `FastStackConfig` + `setup_app()` | Their `main.py` calling `setup_app()` with overrides |
| Structured logger, middleware, health checks | Middleware configuration via `FastStackConfig` |

### The "Own Your Business Code" Principle

- **Framework provides plumbing**: base classes, protocols, exceptions, middleware, database
- **Generator creates business code**: models, schemas, services, routers, tests, fakes
- **User customizes business code**: add logic to service hooks, extend repos, modify routers
- **Some files can be regenerated**, others are preserved (see table below)

### File Ownership

| File Type | Status | Meaning |
|-----------|--------|---------|
| Schemas (Pydantic Create/Update/Response) | REGENERATABLE | Derived from model, safe to overwrite |
| Fakes (in-memory test repos) | REGENERATABLE | Derived from model, safe to overwrite |
| Factories (polyfactory) | REGENERATABLE | Derived from schema, safe to overwrite |
| Dependencies (Depends chains) | REGENERATABLE | Derived from model, safe to overwrite |
| Models (SQLAlchemy) | PRESERVED | User adds fields, constraints, custom columns |
| Repositories | PRESERVED | User adds custom query methods |
| Services | PRESERVED | User adds business logic to hooks and custom methods |
| Routers | PRESERVED | User modifies endpoints, adds routes |
| Tests | PRESERVED | User adds test cases beyond generated ones |

---

## CLI Commands

```bash
# Install
pip install faststack              # Installs both faststack_core + CLI

# Project scaffolding
faststack init my-project                            # Interactive: asks for modules
faststack init my-project --entities entities.yaml   # Pre-define entities

# Entity management
faststack add-entity Product                         # Interactive: asks for fields
faststack add-entity Product --fields "name:string:required,price:decimal"
faststack add-entity Product --from-yaml entities.yaml  # From YAML definition
faststack add-entity Product --from-yaml entities.yaml --update  # Merge new fields into existing entity

# Code regeneration (model-first)
faststack generate Product                           # Regenerate schemas/fakes from model
faststack generate --all                             # Regenerate all entities

# Database (Alembic wrapper)
faststack migrate generate "add posts table"         # Autogenerate migration from model changes
faststack migrate upgrade                            # Apply all pending migrations
faststack migrate downgrade                          # Roll back one migration

# Status
faststack list                                       # Show all entities, generation status, staleness
```

### Alembic Integration Details

Generated at `faststack init` time: `alembic/` directory with `env.py`, `versions/`, `script.py.mako`, and `alembic.ini`.

The generated `env.py`:
1. **Auto-imports all models.** Scans `app/models/*.py` so Alembic's autogenerate detects all changes. No manual import list maintenance.
2. **Uses async engine.** Matches our async-first architecture:
   ```python
   async def run_migrations_online():
       engine = create_async_engine(settings.database_url)
       async with engine.connect() as conn:
           await conn.run_sync(do_run_migrations)
   ```
3. **Reads database URL from project config.** Single source of truth — not duplicated in `alembic.ini`.

`faststack add-entity` does NOT auto-migrate. It prints: `Run 'faststack migrate generate "add product"' to create the migration.`

Not in scope: custom migration DSL, multi-database support, migration squashing (all available via raw Alembic).

---

## Generated Project Structure (Simple Mode)

```
my-project/
├── app/
│   ├── __init__.py
│   ├── main.py                        # FastAPI app factory (imports from faststack_core)
│   ├── config.py                      # Pydantic v2 Settings
│   ├── models/
│   │   ├── __init__.py
│   │   └── {entity}.py               # SQLAlchemy model (inherits faststack_core base) [PRESERVED]
│   ├── schemas/
│   │   └── {entity}.py               # Pydantic v2: Create, Update, Response, DetailResponse [REGENERATABLE]
│   ├── repositories/
│   │   └── {entity}.py               # Extends SqlAlchemyRepository, user adds custom queries [PRESERVED]
│   ├── services/
│   │   └── {entity}.py               # Extends CrudService, user adds business logic [PRESERVED]
│   └── api/
│       ├── dependencies.py           # Depends() factories [REGENERATABLE]
│       └── routes/
│           └── {entity}.py           # FastAPI router [PRESERVED]
├── tests/
│   ├── conftest.py
│   ├── factories/{entity}.py          # polyfactory [REGENERATABLE]
│   ├── unit/
│   │   ├── fakes/{entity}_repository.py  # In-memory fake [REGENERATABLE]
│   │   └── test_{entity}_service.py      # Service tests [PRESERVED]
│   └── integration/
│       └── test_{entity}_api.py          # Endpoint tests [PRESERVED]
├── alembic/
│   ├── env.py                         # Async, auto-discovers models
│   └── versions/
├── entities.yaml
├── .project-config.yaml              # Enabled modules, generation hashes
├── pyproject.toml                    # Depends on faststack
├── Dockerfile
├── docker-compose.yml
└── .pre-commit-config.yaml
```

---

## Runtime Core (`faststack_core`)

### Async-First

All repository and service methods are `async def`. The database session uses `AsyncSession` from SQLAlchemy 2.0's async engine. Alembic migrations stay sync (Alembic's runner is sync; this is standard practice).

### Base Entity Classes

```python
# faststack_core/base/entity.py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, Boolean, String
from datetime import datetime
import uuid

class Base(DeclarativeBase):
    pass

class Entity(Base):
    """Base with UUID primary key."""
    __abstract__ = True
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

class AuditedEntity(Entity):
    """Adds created/updated tracking."""
    __abstract__ = True
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.now, onupdate=datetime.now)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

class SoftDeleteEntity(Entity):
    """Adds soft delete support."""
    __abstract__ = True
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    deleted_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

class FullAuditedEntity(AuditedEntity, SoftDeleteEntity):
    """Combines audit + soft delete. Recommended default."""
    __abstract__ = True
```

### Repository Protocol + Implementation

A `Protocol` defines the contract. Concrete classes implement it via structural typing — no inheritance required for fakes.

```python
# faststack_core/base/repository.py — the contract
from typing import Protocol, Generic, TypeVar

class Repository(Protocol[T]):
    """Base repository contract. All methods async."""
    async def get_by_id(self, id: UUID) -> T | None: ...
    async def list(self, skip: int = 0, limit: int = 100) -> list[T]: ...
    async def create(self, data: dict) -> T: ...
    async def update(self, id: UUID, data: dict) -> T: ...
    async def delete(self, id: UUID) -> None: ...
    async def count(self) -> int: ...

class SearchableRepository(Repository[T], Protocol):
    """Extended contract with search/filter/sort."""
    async def search(self, query: str, fields: list[str], skip: int = 0, limit: int = 100) -> list[T]: ...
    async def list(self, skip: int = 0, limit: int = 100, sort_by: str | None = None) -> list[T]: ...
```

```python
# faststack_core/base/repository.py — SQLAlchemy implementation
class SqlAlchemyRepository(Generic[T]):
    """Async SQLAlchemy implementation. Satisfies Repository protocol."""
    def __init__(self, db: AsyncSession, model: type[T]):
        self.db = db
        self.model = model

    async def get_by_id(self, id: UUID) -> T | None:
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def list(self, skip=0, limit=100, sort_by: str | None = None) -> list[T]:
        stmt = select(self.model).offset(skip).limit(limit)
        if sort_by:
            stmt = stmt.order_by(getattr(self.model, sort_by))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, data: dict) -> T:
        entity = self.model(**data)
        self.db.add(entity)
        await self.db.flush()
        await self.db.refresh(entity)
        return entity

    async def update(self, id: UUID, data: dict) -> T:
        entity = await self.get_by_id(id)
        if not entity:
            raise NotFoundError(f"{self.model.__name__} not found")
        for key, value in data.items():
            setattr(entity, key, value)
        await self.db.flush()
        await self.db.refresh(entity)
        return entity

    async def delete(self, id: UUID) -> None:
        entity = await self.get_by_id(id)
        if not entity:
            raise NotFoundError(f"{self.model.__name__} not found")
        if isinstance(entity, SoftDeleteEntity):
            entity.is_deleted = True
            entity.deleted_at = datetime.now()
        else:
            await self.db.delete(entity)
        await self.db.flush()

    async def hard_delete(self, id: UUID) -> None:
        entity = await self.get_by_id(id)
        if not entity:
            raise NotFoundError(f"{self.model.__name__} not found")
        await self.db.delete(entity)
        await self.db.flush()

    async def count(self) -> int:
        result = await self.db.execute(select(func.count()).select_from(self.model))
        return result.scalar_one()
```

### In-Memory Fakes (Generated Per Entity)

A fake is a working implementation of the Repository protocol using a Python dict. Unlike mocks (scripted responses), fakes actually store and retrieve data — tests exercise real behavior.

```python
# Generated: tests/unit/fakes/user_repository.py [REGENERATABLE]
class FakeUserRepository:
    """Satisfies Repository protocol via structural typing — no inheritance needed."""
    def __init__(self):
        self._store: dict[UUID, User] = {}

    async def create(self, data: dict) -> User:
        user = User(id=uuid4(), **data)
        self._store[user.id] = user
        return user

    async def get_by_id(self, id: UUID) -> User | None:
        return self._store.get(id)

    async def get_by_email(self, email: str) -> User | None:
        return next((u for u in self._store.values() if u.email == email), None)

    async def list(self, skip: int = 0, limit: int = 100) -> list[User]:
        items = list(self._store.values())
        return items[skip:skip + limit]

    async def update(self, id: UUID, data: dict) -> User:
        user = self._store.get(id)
        if not user:
            raise NotFoundError("User not found")
        for key, value in data.items():
            setattr(user, key, value)
        return user

    async def delete(self, id: UUID) -> None:
        if id not in self._store:
            raise NotFoundError("User not found")
        del self._store[id]

    async def count(self) -> int:
        return len(self._store)
```

### CRUD Service with Lifecycle Hooks

```python
# faststack_core/base/service.py
class CrudService(Generic[T]):
    def __init__(self, repository: Repository[T]):
        self.repository = repository

    # Override these hooks in your generated service
    async def before_create(self, data): return data
    async def after_create(self, entity): return entity
    async def before_update(self, id, data): return data
    async def after_update(self, entity): return entity
    async def before_delete(self, id): pass
    async def after_delete(self, id): pass

    async def create(self, data) -> T:
        data = await self.before_create(data)
        entity = await self.repository.create(data)
        return await self.after_create(entity)

    async def get(self, id: UUID) -> T:
        entity = await self.repository.get_by_id(id)
        if not entity:
            raise NotFoundError(f"Entity {id} not found")
        return entity

    async def list(self, skip: int = 0, limit: int = 100) -> list[T]:
        return await self.repository.list(skip=skip, limit=limit)

    async def update(self, id: UUID, data) -> T:
        data = await self.before_update(id, data)
        entity = await self.repository.update(id, data)
        return await self.after_update(entity)

    async def delete(self, id: UUID) -> None:
        await self.before_delete(id)
        await self.repository.delete(id)
        await self.after_delete(id)
```

### Exception Hierarchy + RFC 7807

```python
# faststack_core/exceptions/domain.py
class DomainError(Exception):
    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}

class NotFoundError(DomainError): ...
class AlreadyExistsError(DomainError): ...
class ValidationError(DomainError): ...
class OperationNotAllowedError(DomainError): ...
class ResourceConflictError(DomainError): ...
class InsufficientPermissionsError(DomainError): ...
class ExternalServiceError(DomainError): ...
class ConfigurationError(DomainError): ...

# faststack_core/exceptions/handlers.py
def register_exception_handlers(app: FastAPI):
    """Register RFC 7807 handlers. Called by setup_app()."""
    @app.exception_handler(DomainError)
    async def domain_error_handler(request, exc):
        status = EXCEPTION_MAP.get(type(exc), 500)
        return JSONResponse(
            status_code=status,
            content={
                "type": f"/errors/{type(exc).__name__}",
                "title": type(exc).__name__,
                "status": status,
                "detail": exc.message,
                "instance": str(request.url),
            }
        )
```

### `setup_app()` Configuration

Dataclass config with sensible defaults. Not Pydantic `BaseSettings` — this is code-level config, not env-based. The user's `config.py` (Pydantic Settings) can feed values in, but that's their choice.

```python
# faststack_core/settings/config.py
from dataclasses import dataclass, field

@dataclass
class FastStackConfig:
    # Middleware toggles
    correlation_id: bool = True
    request_logging: bool = True
    security_headers: bool = True

    # CORS (None = disabled, provide origins to enable)
    cors_origins: list[str] | None = None

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"          # "json" or "text"
    sensitive_fields: list[str] = field(default_factory=lambda: [
        "password", "secret", "token", "api_key", "authorization"
    ])

    # Health checks
    health_check: bool = True
    health_check_path: str = "/health"

    # Exception handlers
    exception_handlers: bool = True    # RFC 7807 handlers
```

```python
# In generated main.py:
from faststack_core.setup import setup_app
from faststack_core.settings.config import FastStackConfig

app = FastAPI()
setup_app(app)                          # all defaults
# or:
setup_app(app, FastStackConfig(
    cors_origins=["http://localhost:3000"],
    request_logging=False,
    log_level="DEBUG",
))
```

Each boolean toggle controls whether `setup_app` calls `app.add_middleware(...)` for that component. `sensitive_fields` extends the default masking list.

---

## Logging & Observability (from mcp-context-forge)

Inspired by [IBM/mcp-context-forge](https://github.com/IBM/mcp-context-forge)'s production-grade logging.

### Structured Logger

```python
# faststack_core/logging/structured_logger.py
# Dual-format: JSON to files (machine-readable), colored text to console (human-readable)
# Auto-enrichment: correlation_id, hostname, process_id, timestamp
# Configurable via FastStackConfig: log_level, log_format

class StructuredLogger:
    """Production-grade logger with dual output."""
    def setup(self, app_name: str, log_level: str = "INFO"):
        # Console handler: colored text for development
        # File handler: JSON for log aggregation (ELK, CloudWatch, etc.)
        ...
```

### Correlation ID Middleware

```python
# faststack_core/middleware/correlation_id.py
class CorrelationIdMiddleware:
    async def dispatch(self, request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))
        token = correlation_id_var.set(correlation_id)
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
```

### Request Logging Middleware

```python
# faststack_core/middleware/request_logging.py
# Logs: method, path, status_code, duration_ms, client_ip, user_agent
# Masks sensitive data in request/response bodies (passwords, tokens, keys)

class RequestLoggingMiddleware:
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info("request_completed", extra={
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "correlation_id": get_correlation_id(),
        })
        return response
```

### Sensitive Data Masking

```python
# faststack_core/logging/masking.py
# Recursive masking of sensitive fields in dicts/logs
# Default patterns: password, secret, token, api_key, authorization, credit_card
# Extensible via FastStackConfig.sensitive_fields
# Depth-limited to prevent performance issues on large payloads

def mask_sensitive_data(data: dict, depth: int = 5) -> dict:
    """Recursively mask values for keys matching sensitive patterns."""
    ...
```

### Health Check Endpoints

```python
# faststack_core/health/endpoints.py
# GET /health → {"status": "ok"}
# GET /health/detailed → {"status": "ok", "database": "connected", "version": "1.0.0", "uptime": "2h 15m"}

def create_health_router(db_dependency, app_version: str) -> APIRouter:
    ...
```

---

## Entity YAML Format

```yaml
# entities.yaml
entities:
  User:
    base: FullAuditedEntity
    fields:
      email: {type: string, unique: true, required: true}
      name: {type: string, required: true}
      role: {type: enum, values: [admin, editor, viewer], default: '"viewer"'}
      bio: {type: text}
    searchable: [email, name]

  Post:
    base: AuditedEntity
    fields:
      title: {type: string, required: true}
      content: {type: text}
      status: {type: enum, values: [draft, published, archived], default: '"draft"'}
      tags: {type: array, items: string}
      metadata: {type: jsonb}
      user_id: {type: uuid, references: User}
    searchable: [title]

  Category:
    base: AuditedEntity
    fields:
      name: {type: string, required: true}
      parent_id: {type: uuid, references: self}
```

### Type Mapping

| YAML type | SQLAlchemy | Pydantic | Python | TypeScript |
|-----------|------------|----------|--------|------------|
| string | String(255) | str | str | string |
| text | Text | str | str | string |
| integer | Integer | int | int | number |
| float | Float | float | float | number |
| boolean | Boolean | bool | bool | boolean |
| datetime | DateTime | datetime | datetime | string (ISO) |
| date | Date | date | date | string |
| uuid | UUID(as_uuid=True) | UUID4 | uuid.UUID | string |
| decimal | Numeric(p,s) | Decimal | Decimal | number |
| json | JSON | dict | dict | Record<string, any> |
| enum | Enum(PythonEnum) | Literal[...] | str, enum.Enum | union of string literals |
| array | ARRAY(inner) (Postgres) | list[inner] | list | inner[] |
| jsonb | JSONB | dict | dict | Record<string, unknown> |

Enum generates a `str, enum.Enum` subclass in the model file (e.g., `class PostStatus(str, enum.Enum)`) so values serialize cleanly to JSON. Array is PostgreSQL-only. JSONB is distinct from JSON — indexable and supports PostgreSQL operators.

Not in v1: custom user-defined types, file/upload types, composite types. Users add these manually to their PRESERVED model files.

### Relationship Handling

**Three relationship types:**

| YAML syntax | Relationship | Example |
|---|---|---|
| `user_id: {type: uuid, references: User}` | Many-to-one | Post belongs to User |
| `tags: {type: many_to_many, references: Tag}` | Many-to-many | Post has many Tags |
| `parent_id: {type: uuid, references: self}` | Self-referential | Category tree |

One-to-one is many-to-one with a unique constraint — no special syntax needed.

**Generated output per relationship:**

Model layer:
```python
user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
user: Mapped["User"] = relationship(back_populates="posts")
```

Schema layer — two response variants:
```python
class PostResponse(BaseModel):       # Default: ID-only (list endpoints, avoids N+1)
    user_id: UUID

class PostDetailResponse(BaseModel):  # Nested object (detail endpoints, eager load)
    user: UserResponse
```

Router layer — flat routes only:
```
GET    /posts          # filterable by ?user_id=xxx
GET    /posts/{id}     # detail with nested user
POST   /posts          # user_id in body
```

No nested routes (`/users/{id}/posts`). Query params achieve the same filtering without coupling routers. Users can add nested routes — routers are PRESERVED files.

**Cascade behavior:**

| Relationship | Default | Configurable via |
|---|---|---|
| Many-to-one | `ON DELETE SET NULL` | `on_delete: cascade\|set_null\|restrict` in YAML |
| Many-to-many | Cascade delete on junction table only | Not configurable in v1 |
| Self-referential | `ON DELETE SET NULL` | Same as many-to-one |

Not in v1: polymorphic inheritance, composite foreign keys, through-model customization on many-to-many.

---

## YAML Evolution & Source of Truth

### Two paths, both supported

**Path 1: Model-first (recommended for day-to-day)**

User edits the SQLAlchemy model directly, then regenerates derived files:
```bash
# 1. Edit app/models/user.py — add 'bio' field
# 2. Regenerate schemas/fakes from model
faststack generate User
# 3. Create migration
faststack migrate generate "add bio to users"
```

`faststack generate` uses AST-based introspection — reads the Python file, extracts fields/types, regenerates REGENERATABLE files. Never imports the module, so it works without a running database.

**Path 2: YAML-first (for bulk changes or new entities)**
```bash
# 1. Edit entities.yaml
# 2. Update existing entity from YAML
faststack add-entity User --from-yaml entities.yaml --update
# 3. Create migration
faststack migrate generate "update user fields"
```

`--update` flag merges new fields into the existing model instead of failing.

### Source of truth

The **model file** is always the source of truth. The YAML is an input format, not a living schema. After initial generation, YAML may drift from the model — that's fine. `faststack generate` reads the model, not the YAML. Matches Django's pattern: edit `models.py`, run `makemigrations`.

### Change detection

`faststack list` shows generation status:
```
Entity      Model                    Last Generated    Status
User        app/models/user.py       2026-03-28        schemas outdated (model changed)
Post        app/models/post.py       2026-03-28        up to date
```

Compares a hash of the model file against what was last used to generate (stored in `.project-config.yaml`).

---

## Escape Hatches

Explicitly documented paths for when users outgrow the framework's abstractions.

### Repository level

Users add custom query methods to their generated repository (PRESERVED):
```python
class ProductRepository(SqlAlchemyRepository[Product]):
    # Base CRUD inherited from SqlAlchemyRepository

    # User adds custom queries:
    async def find_by_price_range(self, min: Decimal, max: Decimal) -> list[Product]:
        result = await self.db.execute(
            select(self.model).where(self.model.price.between(min, max))
        )
        return list(result.scalars().all())
```

Full access to `self.db` (`AsyncSession`). The real repo inherits `SqlAlchemyRepository` for CRUD convenience. Services depend on the `Repository` Protocol — so fakes work via structural typing.

### Service level

Lifecycle hooks cover CRUD customization. For non-CRUD logic, add methods:
```python
class OrderService(CrudService[Order]):
    async def checkout(self, order_id: UUID) -> Order:
        order = await self.repository.get_by_id(order_id)
        if not order:
            raise NotFoundError("Order not found")
        # ... custom checkout logic
        return order
```

### Middleware level

Users add their own middleware before or after `setup_app()`:
```python
app = FastAPI()
setup_app(app, config)
app.add_middleware(MyCustomMiddleware)  # standard FastAPI
```

### Full opt-out

Any component can be disabled via `FastStackConfig` booleans. Set `exception_handlers=False` and register your own. Skip `CrudService` and write a plain class that takes a `Repository` protocol.

**Principle:** FastStack is composable pieces, not a locked box. The framework helps when you follow the pattern and steps aside when you don't.

---

## Testing Strategy

### In Generated Projects

**Unit tests (per entity) — in-memory fakes:**
```python
# tests/unit/fakes/user_repository.py [REGENERATABLE]
class FakeUserRepository:
    """Satisfies Repository protocol. Stores data in a dict."""
    def __init__(self):
        self._store: dict[UUID, User] = {}
    async def create(self, data): ...
    async def get_by_id(self, id): ...
    # Same interface as Repository protocol

# tests/unit/test_user_service.py [PRESERVED]
async def test_create_user_validates_email():
    repo = FakeUserRepository()
    service = UserService(repo)
    result = await service.create(UserCreate(email="test@test.com", name="Test"))
    assert result.email == "test@test.com"

async def test_duplicate_email_raises():
    repo = FakeUserRepository()
    service = UserService(repo)
    await service.create(UserCreate(email="taken@test.com", name="Test"))
    with pytest.raises(AlreadyExistsError):
        await service.create(UserCreate(email="taken@test.com", name="Test2"))
```

**Integration tests — real DB via TestClient:**
```python
# tests/integration/test_user_api.py [PRESERVED]
async def test_create_user_endpoint(client):
    response = await client.post("/users", json={"email": "test@test.com", "name": "Test"})
    assert response.status_code == 201
    assert response.json()["email"] == "test@test.com"
```

**Test factories:**
```python
# tests/factories/user.py [REGENERATABLE]
from polyfactory.factories.pydantic_factory import ModelFactory
class UserCreateFactory(ModelFactory):
    __model__ = UserCreate
```

### Framework Tests

```
tests/
├── test_core/
│   ├── test_base_entity.py        # Base class behavior
│   ├── test_repository.py         # Protocol conformance, SqlAlchemyRepository, soft-delete
│   ├── test_crud_service.py       # Lifecycle hooks
│   └── test_exceptions.py        # RFC 7807 formatting
├── test_cli/
│   ├── test_init.py              # Project scaffolding
│   ├── test_add_entity.py        # Entity generation
│   ├── test_generate.py          # Model-first regeneration
│   └── test_yaml_parser.py       # YAML parsing + type mapping
└── test_templates/
    └── test_simple_mode.py        # All simple templates render correctly
```

---

## Build Sequence

### v1 Scope

#### Phase 1: Runtime Core
1. `faststack_core/base/entity.py` — Entity, AuditedEntity, SoftDeleteEntity, FullAuditedEntity
2. `faststack_core/base/repository.py` — Repository Protocol + SqlAlchemyRepository (async)
3. `faststack_core/base/service.py` — CrudService with async lifecycle hooks
4. `faststack_core/exceptions/domain.py` — Full exception hierarchy
5. `faststack_core/exceptions/handlers.py` — RFC 7807 global handlers
6. `faststack_core/database/session.py` — DatabaseConfig, async get_db
7. `faststack_core/base/permissions.py` — @require_permission, @require_role
8. Tests for all core components

#### Phase 2: Logging & Middleware
9. `faststack_core/logging/structured_logger.py` — Dual-format structured logger
10. `faststack_core/logging/masking.py` — Sensitive data masking
11. `faststack_core/logging/config.py` — Log configuration
12. `faststack_core/middleware/correlation_id.py` — UUID per request
13. `faststack_core/middleware/request_logging.py` — HTTP request/response logging
14. `faststack_core/middleware/security_headers.py` — Standard security headers
15. `faststack_core/health/endpoints.py` — Health check routes
16. `faststack_core/settings/config.py` — FastStackConfig dataclass
17. `faststack_core/setup.py` — One-call setup with configurable toggles
18. Tests for logging, middleware, health checks, config

#### Phase 3: CLI Foundation + YAML Parser
19. CLI framework (click)
20. `cli/yaml_parser.py` — Parse entities.yaml, type mapping (13 types), relationship resolution
21. `cli/field_mappings.py` — YAML → SQLAlchemy → Pydantic type map
22. `cli/model_introspector.py` — AST-based model reader for regeneration
23. Tests for parser, field mappings, and introspector

#### Phase 4: Project Scaffolding (`faststack init`)
24. `templates/project/` — All project-level templates (main.py, config.py, pyproject.toml, Docker, Alembic env.py)
25. `cli/cmd_init.py` — Project scaffolding command (simple mode only)
26. Tests: generate project, verify structure, verify async env.py

#### Phase 5: Simple Mode Entity Templates
27. `templates/simple/model.py.j2` — SQLAlchemy model with relationships, enums
28. `templates/simple/schema.py.j2` — Pydantic v2 Create/Update/Response/DetailResponse
29. `templates/simple/repository.py.j2` — Extends SqlAlchemyRepository
30. `templates/simple/service.py.j2` — Extends CrudService with hooks
31. `templates/simple/router.py.j2` — FastAPI CRUD endpoints (flat routes, query param filtering)
32. `templates/simple/factory.py.j2` — polyfactory
33. `templates/simple/fake_repository.py.j2` — In-memory fake (satisfies Protocol)
34. `templates/simple/test_unit_service.py.j2`
35. `templates/simple/test_integration.py.j2`

#### Phase 6: Entity CLI Commands
36. `cli/cmd_add_entity.py` — Add entity (interactive or with flags, `--update` for existing)
37. `cli/cmd_generate.py` — Regenerate from model (AST introspection, hash tracking)
38. `cli/cmd_migrate.py` — Alembic wrapper (generate, upgrade, downgrade)
39. `cli/cmd_list.py` — Show entities, generation status, staleness detection
40. Registry file generation (dependencies.py, router registration)

### v2 Roadmap (Deferred)

These remain as planned features but are deferred to keep v1 focused and shippable.

#### DDD Mode (Onion Architecture)

**What it adds:** A second architecture mode chosen at `faststack init --arch ddd` time, with domain entities as pure Python dataclasses separated from SQLAlchemy DTOs.

**v1 vs v2 example — defining a User entity:**

v1 (simple mode) — the model IS the ORM model:
```python
# app/models/user.py — SQLAlchemy model, single file
class User(FullAuditedEntity):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(255))
```

v2 (DDD mode) — domain entity is pure Python, separate from persistence:
```python
# app/domain/user/entities/user.py — no SQLAlchemy imports
@dataclass
class User:
    id: UserId
    email: Email          # Value object with validation
    name: str

    @staticmethod
    def create(email: str, name: str) -> "User":
        return User(id=UserId.generate(), email=Email(email), name=name)

# app/infrastructure/postgres/user/user_dto.py — SQLAlchemy DTO
class UserDTO(FullAuditedEntity):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(255), unique=True)

    def to_entity(self) -> User: ...
    @staticmethod
    def from_entity(user: User) -> "UserDTO": ...
```

**Why defer:** 18 templates (vs 9 for simple mode), doubles test surface. dddpy's own limitations show this is hard — it only handles a single aggregate with no cross-aggregate transaction patterns or bounded context boundaries. Deserves its own design cycle.

#### Auth Module

**What it adds:** JWT authentication, role-based access control, user management endpoints.

**v1 vs v2 example — protecting an endpoint:**

v1 — user implements auth themselves:
```python
# User writes their own auth dependency and middleware
# FastStack provides @require_permission decorator but no auth module
```

v2 — generated auth module:
```bash
faststack init my-app --with-auth
# Generates: app/modules/auth/ with:
#   - POST /auth/register, /auth/login, /auth/refresh, /auth/me
#   - User, Role, Permission models
#   - JWT token service (from faststack_core.auth)
#   - AuthMiddleware that populates request.state.user
```

**Why defer:** Substantial scope (JWT + RBAC + 4 endpoints + user/role models). Auth is highly opinionated — users often need to customize heavily. They can add their own auth using the PRESERVED service/router pattern.

#### Events + Background Jobs

**What it adds:** In-process domain event bus and background job integration.

**v1 vs v2 example — reacting to entity creation:**

v1 — user handles side effects in service hooks:
```python
class OrderService(CrudService[Order]):
    async def after_create(self, order):
        # User manually calls notification service, etc.
        await self.notification_service.send_order_confirmation(order)
        return order
```

v2 — domain events decouple producers from consumers:
```python
# Service publishes event
class OrderService(CrudService[Order]):
    async def after_create(self, order):
        await self.event_bus.publish(OrderCreated(order_id=order.id))
        return order

# Separate handler subscribes
@event_handler(OrderCreated)
async def send_confirmation(event: OrderCreated):
    await notification_service.send_order_confirmation(event.order_id)
```

**Why defer:** Most CRUD apps don't need event-driven architecture on day one. Service hooks handle simple side effects. Events add complexity (ordering, error handling, eventual consistency) that only pays off at scale.

#### TypeScript Client Generation

**What it adds:** `faststack generate-client` command that produces TypeScript types, API client, and React Query hooks from the OpenAPI spec.

**v1 vs v2 example:**

v1 — user uses existing tools:
```bash
# FastStack generates a standard OpenAPI spec. User picks their own TS generator:
npx openapi-typescript http://localhost:8000/openapi.json -o src/api/types.ts
# or
npx orval --input http://localhost:8000/openapi.json
```

v2 — integrated generation:
```bash
faststack generate-client
# Generates: frontend/src/api/types.ts, apiClient.ts, services/, hooks/
```

**Why defer:** `openapi-typescript` and `orval` are mature, well-maintained tools that already solve this. Building custom `.ts.j2` templates is significant work with unclear value. v1 documents how to use existing tools with the generated OpenAPI spec.

#### Multi-Tenancy Module

**What it adds:** Tenant isolation via row-level filtering, tenant CRUD, hierarchical settings.

**v1 vs v2 example:**

v1 — single-tenant, user adds tenant filtering manually if needed.

v2 — automatic tenant isolation:
```bash
faststack init my-app --with-tenant
# Adds MultiTenantMixin to base entities
# All queries automatically filter by tenant_id from JWT/header
# Generates: app/modules/tenant/ with Tenant CRUD
```

**Why defer:** Niche requirement. Most projects are single-tenant. Adds complexity to every query layer.

---

## Key Technical Challenges

| Challenge | Mitigation |
|-----------|-----------|
| PRESERVED vs REGENERATABLE files | Track generation hashes in `.project-config.yaml`; `generate` skips PRESERVED files |
| Model-first regeneration | AST-based model introspection (parse Python file, don't import it) |
| Jinja2 template escaping | Templates are in the framework package, not inside a cookiecutter — no double-Jinja2 conflict |
| Entity pluralization | Use `inflect` library |
| Circular imports from relationships | `TYPE_CHECKING` imports + string-based relationship targets |
| Async Alembic | Generated `env.py` uses `create_async_engine` + `run_sync` bridge |
| Protocol conformance checking | Runtime checks optional; mypy/pyright validate at type-check time |
| Testing the framework itself | Comprehensive test suite with temp directories for generated projects |

---

## Verification Plan

### v1 Verification

1. **Core**: Unit tests for all base classes (entity, repository protocol, SqlAlchemyRepository, service, exceptions)
2. **Async**: Verify all repository/service methods work with `AsyncSession` and `pytest-asyncio`
3. **Simple mode**: `faststack init test-simple` → add User + Post entities → `pytest` → all pass
4. **Fakes**: Verify FakeUserRepository satisfies Repository protocol (mypy + runtime tests)
5. **Regeneration**: Modify a model → `faststack generate Product` → verify schemas/fakes updated, services/repos preserved
6. **Relationships**: User → Post (FK) → verify models, schemas (Response + DetailResponse), and tests handle the relationship
7. **Custom types**: Entity with enum, array, jsonb fields → verify model, schema, migration all correct
8. **Exception flow**: Trigger NotFoundError, AlreadyExistsError → verify RFC 7807 JSON responses
9. **Middleware**: Verify correlation IDs propagate, request logging works, security headers present
10. **Linting**: `ruff check .` and `black --check .` pass on all generated code
11. **Change detection**: `faststack list` correctly shows outdated entities after model changes
