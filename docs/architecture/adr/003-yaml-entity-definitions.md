# ADR-003: YAML Entity Definitions with Model as Source of Truth

- *Status:* Accepted
- *Date:* 2026-03-30
- *Deciders:* Manav
- *Related:* [ADR-006](006-file-ownership-model.md)

## Context

Users need to define entities (fields, types, relationships) to generate code. The question: what input format, and what is the source of truth after initial generation?

Two competing philosophies:
1. **Schema-first** — a definition file (YAML, DBML, GraphQL SDL) is always the source of truth. All code is derived from it.
2. **Model-first** — the Python model file is the source of truth. Definition files are input formats for initial generation only.

Schema-first seems cleaner but creates a problem: users inevitably customize their models (add constraints, computed properties, custom columns). The schema file can't represent all of SQLAlchemy's capabilities. It becomes a bottleneck.

Django's pattern is model-first: you edit `models.py`, run `makemigrations`. The initial scaffolding helps you start, but the model is what you live with.

## Decision

**YAML as input format. Model file as source of truth.**

- `entities.yaml` is used at `faststack init` time and by `faststack add-entity --from-yaml`
- After generation, the SQLAlchemy model file is the source of truth
- `faststack generate` reads the model via AST introspection (never imports it) and regenerates REGENERATABLE files
- YAML may drift from the model after generation — that's fine
- `faststack add-entity --update` merges new YAML fields into an existing model
- `faststack list` detects staleness by comparing model file hash against last generation hash

YAML supports 13 types (string, text, integer, float, boolean, datetime, date, uuid, decimal, json, enum, array, jsonb) and 3 relationship types (many-to-one, many-to-many, self-referential).

## Consequences

### Positive
- Users can customize models freely without fighting a schema file
- AST introspection means `faststack generate` works without a running database or importable code
- Matches Django's proven model-first pattern — familiar to Python devs
- YAML is still useful for bulk initial setup and new entity scaffolding

### Negative
- YAML drifts from models over time — can cause confusion if users expect YAML to be authoritative
- AST parsing is more complex than reading a schema file — must handle SQLAlchemy's `Mapped[]` syntax, relationships, and custom types
- No round-trip: changes to models don't back-propagate to YAML

### Neutral
- v2 may add DBML as an alternative input format — the model-first philosophy wouldn't change

## Alternatives Considered

| Option | Why Not |
|--------|---------|
| YAML as permanent source of truth (schema-first) | Can't represent all SQLAlchemy capabilities. Users fight the YAML when adding constraints, computed columns, or dialect-specific features. |
| DBML as input | Richer than YAML for database modeling, but adds a dependency and learning curve. Good v2 option, not v1. |
| No YAML — always define entities via CLI flags | Tedious for projects with 5+ entities. YAML is better for bulk definition. |
| GraphQL SDL as input | Over-engineered for entity definition. Adds unnecessary conceptual overhead. |

## Configuration

- `entities.yaml` at project root — user-editable input file
- `.project-config.yaml` — stores generation hashes for staleness detection

## References

- [Django model-first philosophy](https://docs.djangoproject.com/en/5.0/topics/db/models/)
- [DBML — Database Markup Language](https://dbml.dbdiagram.io/)
