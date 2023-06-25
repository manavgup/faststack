# ADR-007: v1 Scope Boundary

- *Status:* Accepted
- *Date:* 2026-03-30
- *Deciders:* Manav
- *Related:* All other ADRs

## Context

The original plan had 12 phases covering: runtime core, logging/middleware, CLI, project scaffolding, simple mode templates, DDD mode templates, entity CLI commands, auth module, events/background jobs, TypeScript client, multi-tenancy, and polish.

Research into reference projects revealed:
- DDD mode (18 templates) doubles the test surface. dddpy only handles a single aggregate — no cross-aggregate patterns exist to reference.
- TypeScript client generation is solved by `openapi-typescript` and `orval`.
- Auth, events, and multi-tenancy are each substantial projects that could expand to consume more time than the core framework.

The question: what's the minimum shippable product that fills the gap none of the reference projects fill?

## Decision

**v1 ships simple mode only. DDD, auth, events, frontend, and multi-tenancy are v2.**

### v1 scope (6 phases, ~40 items)

| Phase | What |
|-------|------|
| 1 | Runtime core — entity bases, Repository Protocol, SqlAlchemyRepository, CrudService, exceptions, RFC 7807 |
| 2 | Logging & middleware — structured logger, correlation IDs, request logging, masking, health checks, FastStackConfig, setup_app() |
| 3 | CLI foundation — click framework, YAML parser (13 types, 3 relationship types), field mappings, AST model introspector |
| 4 | Project scaffolding — `faststack init` with simple mode, all project templates including async Alembic env.py |
| 5 | Simple mode entity templates — 9 templates (model, schema, repository, service, router, factory, fake, unit test, integration test) |
| 6 | Entity CLI commands — `add-entity`, `generate`, `migrate`, `list` |

### v2 roadmap (deferred, remains documented in plan)

| Feature | Why Deferred |
|---------|-------------|
| DDD mode (onion architecture) | 18 templates, doubles surface, reference implementations are immature. Needs its own design cycle. |
| Auth module | Substantial (JWT + RBAC + 4 endpoints). Highly opinionated — users customize heavily. |
| Events + background jobs | CRUD apps don't need domain events day one. Service hooks handle simple side effects. |
| TypeScript client generation | `openapi-typescript` and `orval` exist. Document integration instead. |
| Multi-tenancy | Niche. Adds complexity to every query layer. |

## Consequences

### Positive
- Focused, shippable v1 — fills a real gap (Protocol-based testing + async repos + CLI generation + structured logging)
- Faster time to feedback — ship, learn, iterate
- DDD mode gets a proper design cycle instead of being rushed
- Simpler test matrix — 9 templates instead of 27

### Negative
- Users wanting DDD must wait for v2 or structure it themselves
- No built-in auth — users must add their own JWT/RBAC (FastStack provides `@require_permission` decorator but no auth module)
- No integrated TypeScript client — users must run external tools

### Neutral
- v2 features remain fully documented in the plan as the roadmap — nothing is cut, only sequenced
- Users can still use the PRESERVED pattern to hand-build any v2 feature in their own projects

## Alternatives Considered

| Option | Why Not |
|--------|---------|
| Ship all 12 phases as v1 | Scope creep risk. Phases 8-11 could each expand to more effort than phases 1-6 combined. Ships later, not better. |
| Ship simple + DDD in v1, defer modules | DDD alone doubles the template and test surface. Still too much for a focused v1. |
| Ship only runtime core (no CLI) in v1 | A framework without a generator is just a library. The CLI is what makes FastStack a productivity tool. |

## References

- [dddpy limitations](https://github.com/iktakahiro/dddpy) — single aggregate, no cross-aggregate patterns
- [openapi-typescript](https://github.com/openapi-ts/openapi-typescript) — existing TS generation tool
- [orval](https://github.com/orval-labs/orval) — existing TS generation tool with React Query support
