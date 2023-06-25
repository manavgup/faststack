# ADR-002: Protocol-Based Repositories with In-Memory Fakes

- *Status:* Accepted
- *Date:* 2026-03-30
- *Deciders:* Manav
- *Related:* [ADR-001](001-async-first-no-sync.md), [ADR-006](006-file-ownership-model.md)

## Context

The repository layer is the seam between business logic and data access. The choice of abstraction mechanism determines testability, coupling, and developer ergonomics.

Three approaches exist in the Python ecosystem:
1. **Concrete class** (FastForge) — services depend on `SqlAlchemyRepository` directly. No abstraction. Testing requires a real database.
2. **ABC** (dddpy) — abstract base class defines the interface. Fakes must inherit from the ABC. Forces inheritance coupling.
3. **Protocol** (greeden.me blog) — structural typing. Any class with matching methods satisfies the contract. No inheritance required.

We also needed to decide: mocks vs fakes for testing. Mocks return scripted responses ("when `get_by_email` is called, return X"). Fakes actually store and retrieve data using a dict — tests exercise real behavior.

## Decision

**Protocol defines the contract. In-memory fakes for testing.**

Three layers:
- `Repository(Protocol[T])` — the contract, lives in `faststack_core`
- `SqlAlchemyRepository(Generic[T])` — the async SQLAlchemy implementation, lives in `faststack_core`
- `FakeXxxRepository` — generated per entity into user's test directory, satisfies Protocol via structural typing

Optional protocol extensions:
- `Repository` — base CRUD (get_by_id, list, create, update, delete, count)
- `SearchableRepository` — extends with search/filter/sort

Services depend on `Repository` Protocol, never on `SqlAlchemyRepository` directly.

## Consequences

### Positive
- Fakes test real behavior — data actually stored and retrieved, not scripted responses
- No inheritance coupling — fakes don't need to inherit from anything
- Services are decoupled from SQLAlchemy — can swap persistence without touching business logic
- Type checkers (mypy/pyright) validate Protocol conformance at check time
- Unit tests are fast — no database, no I/O

### Negative
- Protocol conformance errors are caught by type checkers, not at runtime (unless we add explicit runtime checks)
- Developers unfamiliar with Python Protocols may find the pattern unfamiliar initially
- Fakes must be kept in sync with the Protocol when methods are added — but they're REGENERATABLE so `faststack generate` handles this

### Neutral
- Real repositories inherit from `SqlAlchemyRepository` for CRUD convenience — this is implementation inheritance, not interface coupling. Services still depend on the Protocol.

## Alternatives Considered

| Option | Why Not |
|--------|---------|
| Concrete class (no abstraction) | FastForge's approach. Testing requires real DB. Services tightly coupled to SQLAlchemy. No swap-ability. |
| ABC (Abstract Base Class) | dddpy's approach. Forces `class FakeUserRepo(UserRepository)` — inheritance coupling for no benefit. Protocol is more Pythonic. |
| Mock objects (unittest.mock) | Scripted responses don't test real behavior. If the repo interface changes, mocks still pass — tests lie. Fakes catch interface drift. |
| SQLAlchemy in-memory SQLite for tests | Slower than dict-based fakes. SQLite has dialect differences from PostgreSQL. Cross-database bugs slip through. |

## References

- [greeden.me — Practical FastAPI + Clean Architecture Guide](https://blog.greeden.me/en/2025/12/23/practical-fastapi-x-clean-architecture-guide/)
- [Python typing.Protocol docs](https://docs.python.org/3/library/typing.html#typing.Protocol)
- [Martin Fowler — Mocks Aren't Stubs](https://martinfowler.com/articles/mocksArentStubs.html)
