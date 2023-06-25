# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) for the FastStack project. Each ADR captures a significant architectural decision, its context, the alternatives considered, and the consequences.

## ADR Index

| # | Title | Status | Date | Section |
|---|-------|--------|------|---------|
| [000](000-adr-template.md) | ADR Template | — | 2026-03-30 | Meta |
| [001](001-async-first-no-sync.md) | Async-First, No Sync Support | Accepted | 2026-03-30 | Framework |
| [002](002-protocol-based-repositories.md) | Protocol-Based Repositories with In-Memory Fakes | Accepted | 2026-03-30 | Framework |
| [003](003-yaml-entity-definitions.md) | YAML Entity Definitions with Model as Source of Truth | Accepted | 2026-03-30 | CLI |
| [004](004-rfc7807-error-responses.md) | RFC 7807 Error Responses with Domain Exception Hierarchy | Accepted | 2026-03-30 | Framework |
| [005](005-crud-service-lifecycle-hooks.md) | CRUD Service Lifecycle Hooks | Accepted | 2026-03-30 | Framework |
| [006](006-file-ownership-model.md) | File Ownership Model (PRESERVED vs REGENERATABLE) | Accepted | 2026-03-30 | CLI |
| [007](007-v1-scope-boundary.md) | v1 Scope Boundary | Accepted | 2026-03-30 | Architecture |
| [008](008-makefile-for-developer-workflow.md) | Makefile for Developer Workflow | Accepted | 2026-03-30 | DX |

## Status Lifecycle

- **Proposed** — under discussion, not yet accepted
- **Accepted** — decision made and in effect
- **Deprecated** — no longer applies, replaced or removed
- **Superseded by ADR-NNN** — replaced by a newer decision
