# ADR-005: CRUD Service Lifecycle Hooks

- *Status:* Accepted
- *Date:* 2026-03-30
- *Deciders:* Manav
- *Related:* [ADR-002](002-protocol-based-repositories.md), [ADR-004](004-rfc7807-error-responses.md)

## Context

Generated CRUD services need a customization mechanism. Users will add business logic — validation, side effects, transformations — to their services. The question: how do they extend generated behavior without fighting the framework?

Three patterns exist:
1. **Override methods** — user subclasses and overrides `create()`, `update()`, etc. Risk: user must remember to call `super()`, or CRUD logic breaks silently.
2. **Lifecycle hooks** — framework calls `before_create()`, `after_create()`, etc. at defined points. User overrides only the hooks. CRUD flow is guaranteed.
3. **Middleware/decorator pattern** — wrap CRUD operations with before/after logic. More flexible but harder to discover and more boilerplate.

## Decision

**Lifecycle hooks on `CrudService`.** Six hooks:

- `before_create(data)` → transform/validate input before persisting
- `after_create(entity)` → side effects after creation (notifications, cache, etc.)
- `before_update(id, data)` → transform/validate before update
- `after_update(entity)` → side effects after update
- `before_delete(id)` → guard/validate before deletion
- `after_delete(id)` → cleanup after deletion

All hooks are `async def` with default no-op implementations. Users override only the hooks they need in their generated service files.

For logic that doesn't fit the CRUD pattern, users add custom methods to their service (escape hatch):
```python
class OrderService(CrudService[Order]):
    async def checkout(self, order_id: UUID) -> Order:
        # Custom non-CRUD business logic
        ...
```

## Consequences

### Positive
- CRUD flow is guaranteed — user can't accidentally skip `db.flush()` or break the create/update/delete sequence
- Discoverable — hooks are listed in the base class, IDE autocomplete shows them
- Minimal boilerplate — override only what you need, default is no-op
- Generated test templates can test hook behavior

### Negative
- Hook granularity is fixed — if a user needs to intercept between `db.add()` and `db.flush()` within `create()`, they must override the full method (escape hatch)
- Six hooks may not cover all patterns — e.g., no `before_list()` or `after_get()` (intentionally omitted to keep it simple)

### Neutral
- Hooks inspired by FastForge's `CrudAppService` — validated pattern in the wild, though FastForge is sync-only

## Alternatives Considered

| Option | Why Not |
|--------|---------|
| Override full CRUD methods | Users must call `super()` correctly. Easy to forget, breaks silently. Hooks avoid this by keeping CRUD flow in the base class. |
| Decorator/middleware pattern | More flexible but harder to discover. Users must learn a wrapping API instead of just overriding a method. Over-engineered for CRUD. |
| Event-based hooks (publish/subscribe) | Over-engineered for v1. Introduces event bus dependency. Deferred to v2 as the domain events module. |
| No hooks — user rewrites service from scratch | Defeats the purpose of code generation. Users would immediately deviate from the generated pattern. |

## References

- [FastForge CrudAppService](https://github.com/Datacrata/fastforge) — similar lifecycle hook pattern (sync)
- [Django signals](https://docs.djangoproject.com/en/5.0/topics/signals/) — event-based alternative (deferred to v2)
