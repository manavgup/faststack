# Contributing to FastStack

## Getting Started

```bash
git clone https://github.com/manavgup/faststack.git
cd faststack
make install-dev    # venv + deps + pre-commit hooks
make check          # verify everything works
```

See [DEVELOPING.md](DEVELOPING.md) for project structure and how code generation works.
See [TESTING.md](TESTING.md) for test organization, markers, and patterns.

## Development Workflow

1. **Create an issue** before starting work on features or non-trivial fixes
2. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/short-description
   ```
3. **Make your changes** — write code, add tests
4. **Run the full check suite:**
   ```bash
   make check    # lint + typecheck + tests with 85% coverage
   ```
5. **Commit** with a clear message:
   ```bash
   git commit -m "Add foo to bar for baz"
   ```
6. **Push and create a PR** against `main`

## Code Standards

### Python

- **Python 3.12+** with type hints
- **Line length:** 120 characters (ruff + black)
- **Formatting:** `make format` (ruff --fix + black)
- **Linting:** `make lint` (ruff + black --check)
- **Type checking:** `make typecheck` (mypy)

### Naming

- `snake_case` for functions, variables, file names
- `PascalCase` for classes
- `UPPER_CASE` for constants

### Tests

- Every feature or bug fix needs tests
- Unit tests for logic, integration tests for CLI commands
- Use fake repositories (Protocol-based), not mocks
- See [TESTING.md](TESTING.md) for patterns

### Templates

When modifying Jinja2 templates in `templates/simple/`:

- Verify rendered output is valid Python: `ast.parse(output)`
- Test with multiple entity types (simple, with FKs, with enums, self-referential)
- Remember the REGENERATABLE vs PRESERVED distinction

## CI Checks

All PRs must pass these required checks before merging:

| Check | Workflow | What it runs |
|-------|----------|--------------|
| Ruff & Black | `lint.yml` | `ruff check .` + `black --check .` |
| Mypy | `lint.yml` | `mypy faststack_core/ cli/` |
| Test (py3.12) | `ci.yml` | `pytest` with 85% coverage threshold |
| Pre-commit | `pre-commit.yml` | All pre-commit hooks |
| Package Build | `ci.yml` | `poetry build` + `twine check` |

Run `make check` locally before pushing — it mirrors the CI gate.

## Commit Messages

Write clear, imperative commit messages:

```
Add entity list command with staleness detection
Fix pluralization for already-plural entity names
Update router template to wire Depends() injection
```

Lead with what the commit does, not what you did. One sentence is usually enough. Add a body only if the "why" isn't obvious.

## Pull Requests

- Keep PRs focused — one feature or fix per PR
- Title: short (under 70 chars), imperative
- Description: what changed and why, not a line-by-line diff
- Link the issue: `Closes #123`

## Architecture Decisions

Non-trivial design decisions are tracked in `docs/architecture/adr/`. If your change introduces a new pattern or overrides an existing decision, add or update an ADR.
