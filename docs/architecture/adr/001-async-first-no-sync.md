# ADR-001: Async-First, No Sync Support

- *Status:* Accepted
- *Date:* 2026-03-30
- *Deciders:* Manav
- *Related:* [ADR-002](002-protocol-based-repositories.md)

## Context

FastAPI's primary value proposition is async Python. SQLAlchemy 2.0 provides mature `AsyncSession` support. The question: should FastStack's runtime core support sync, async, or both?

Supporting both would mean dual interfaces for every repository method, every service method, and every dependency chain — effectively doubling the API surface. Every reference project we studied (FastForge, dddpy, FastAPI full-stack template) uses sync-only, which misses FastAPI's core strength.

## Decision

**Async-only.** All repository and service methods are `async def`. The database session uses `AsyncSession` from `async_sessionmaker`.

- `SqlAlchemyRepository` — all methods are `async def`, use `AsyncSession`
- `CrudService` — all methods and lifecycle hooks are `async def`
- `get_db` — yields `AsyncSession` via `async_sessionmaker`
- In-memory fakes — also `async def` (trivially, since they do no real I/O)
- Alembic migrations — stay sync (Alembic's runner is sync; this is standard practice, using `run_sync` bridge)

## Consequences

### Positive
- Matches FastAPI's async-first identity — users choosing FastAPI expect async
- Single interface to learn, test, and maintain
- Differentiates from all reference projects (all sync-only)
- Simpler codebase — no conditional sync/async branching

### Negative
- Users with sync-only libraries (some legacy ORMs, blocking I/O clients) need to wrap calls in `asyncio.to_thread()`
- Testing requires `pytest-asyncio` — minor friction for users unfamiliar with async testing
- Alembic needs the `run_sync` bridge pattern in `env.py` — a known pattern but not the Alembic default

### Neutral
- SQLAlchemy 2.0's async is production-ready but less battle-tested than its sync API at scale

## Alternatives Considered

| Option | Why Not |
|--------|---------|
| Sync-only | Misses FastAPI's core value prop. Every reference project already does this — no differentiation. |
| Support both sync and async | Doubles the interface surface (every repo method, service method, dependency chain). Massive maintenance burden for v1. Can revisit if demand is clear. |
| Sync with `asyncio.to_thread()` wrapper | Fake async — still blocks the event loop under the wrapper. Worst of both worlds. |

## Configuration

No configuration — async is the only mode. Users needing to call sync code use `asyncio.to_thread()` in their PRESERVED service/repository files.

## References

- [SQLAlchemy 2.0 Async docs](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Alembic async cookbook](https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic)
