# ADR-006: File Ownership Model (PRESERVED vs REGENERATABLE)

- *Status:* Accepted
- *Date:* 2026-03-30
- *Deciders:* Manav
- *Related:* [ADR-003](003-yaml-entity-definitions.md), [ADR-002](002-protocol-based-repositories.md)

## Context

A code generator that can also regenerate code faces a fundamental tension: some generated files should be safely overwritable (derived from the model, no user logic), while others contain user-written business logic that must never be overwritten.

The question: which files are safe to regenerate, and how do we enforce the boundary?

This decision was refined during plan review when we realized repositories must be PRESERVED (not REGENERATABLE as originally planned) because users add custom query methods to them.

## Decision

**Two ownership statuses, tracked in `.project-config.yaml`:**

**REGENERATABLE** — derived from the model, safe to overwrite:
- Schemas (Pydantic Create/Update/Response/DetailResponse)
- Fakes (in-memory test repositories)
- Factories (polyfactory test data)
- Dependencies (FastAPI `Depends()` chains)

**PRESERVED** — generated once, user owns and customizes:
- Models (SQLAlchemy) — user adds fields, constraints, custom columns
- Repositories — user adds custom query methods (e.g., `find_by_price_range`)
- Services — user adds business logic to lifecycle hooks and custom methods
- Routers — user modifies endpoints, adds routes
- Tests — user adds test cases beyond generated ones

`faststack generate` only overwrites REGENERATABLE files. PRESERVED files are skipped with a message: `Skipping {file} (PRESERVED — contains user code)`.

Generation hashes (SHA-256 of the model file at generation time) are stored in `.project-config.yaml`. `faststack list` compares current model hash against stored hash to detect staleness.

## Consequences

### Positive
- Users can fearlessly run `faststack generate` — their business logic is never overwritten
- Clear mental model — "schemas and fakes are derived, everything else is yours"
- Staleness detection tells users when regeneration is needed
- Repositories being PRESERVED enables the escape hatch pattern (custom queries)

### Negative
- PRESERVED files may fall out of sync with model changes — user must manually update repos/services/routers when fields are added/removed
- `.project-config.yaml` is a new file users must not delete — adds a small maintenance surface
- No automatic merging — if a model adds a field, PRESERVED files don't automatically get new methods

### Neutral
- `faststack generate --force` exists as an override to regenerate PRESERVED files — but it prints a warning and requires confirmation

## Alternatives Considered

| Option | Why Not |
|--------|---------|
| All files REGENERATABLE | Destroys user customizations on every regeneration. Unusable after first day. |
| All files PRESERVED (generate once, never touch) | Schemas and fakes would drift from models. Users manually maintain derived code — tedious and error-prone. |
| Git-merge-based regeneration | Complex, error-prone, requires understanding of merge conflicts. Over-engineered for this use case. |
| Comment markers for user sections | Fragile. Users forget to stay within markers. Parsing is brittle. Rails tried this and abandoned it. |

## References

- [Rails generators — skip vs force](https://guides.rubyonrails.org/generators.html) — similar PRESERVED/REGENERATABLE concept
- [FastForge regeneration model](https://github.com/Datacrata/fastforge) — schemas always regenerate, services preserved
