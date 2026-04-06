# Testing FastStack

## Running Tests

```bash
make test                # All tests + 85% coverage gate (CI gate)
make test-unit           # Core + template tests only (fast)
make test-integration    # CLI command tests (scaffold real projects in tmp dirs)
make test-e2e            # End-to-end project scaffold validation
make test-fast           # Everything except @pytest.mark.slow
make test-single K=name  # Run tests matching a keyword
make coverage            # Generate HTML + XML coverage report
```

## Test Organization

```
tests/
├── test_core/           # Unit tests — runtime library
│   ├── test_base_entity.py
│   ├── test_repository.py
│   ├── test_crud_service.py
│   ├── test_exceptions.py
│   ├── test_logging.py
│   ├── test_middleware.py
│   ├── test_health.py
│   └── test_setup.py
├── test_cli/            # Integration tests — CLI commands
│   ├── test_init.py
│   ├── test_add_entity.py
│   ├── test_generate.py
│   ├── test_list.py
│   ├── test_migrate.py
│   ├── test_yaml_parser.py
│   ├── test_model_introspector.py
│   └── test_field_mappings.py
├── test_templates/      # Unit tests — template rendering
│   ├── test_simple_mode.py
│   └── test_project_templates.py
└── test_e2e/            # End-to-end — scaffold + validate
    └── test_smoke.py
```

## Markers

Tests are auto-tagged by directory via `conftest.py` hooks:

| Marker | Directory | What it covers |
|--------|-----------|----------------|
| `unit` | `test_core/`, `test_templates/` | Runtime library, template rendering |
| `integration` | `test_cli/` | CLI commands (scaffolds real projects in tmp dirs) |
| `e2e` | `test_e2e/` | Full project scaffold + validation |
| `slow` | (manual) | Tests taking >1s |

Use markers for selective execution:

```bash
poetry run pytest -m unit           # Only unit tests
poetry run pytest -m "not slow"     # Skip slow tests
```

## Coverage

- **Threshold:** 85% (enforced in `make test` and CI)
- **Report:** `make coverage` generates `htmlcov/index.html`
- **Config:** `[tool.coverage.*]` sections in `pyproject.toml`

Current coverage: ~90% across `faststack_core/` and `cli/`.

## Testing Patterns

### Async Tests

All tests use `asyncio_mode = "auto"` (set in `pyproject.toml`). No need for `@pytest.mark.asyncio` — just write `async def test_*`.

### Fake Repositories

Core tests use in-memory fake repositories that satisfy the `Repository` Protocol via structural typing. No mocks.

```python
from tests.unit.fakes.user_repository import FakeUserRepository

@pytest.fixture
def repo():
    return FakeUserRepository()

@pytest.fixture
def service(repo):
    return UserService(repo)
```

### CLI Tests

CLI tests use Click's `CliRunner` with `monkeypatch.chdir(tmp_path)` to scaffold real projects in temporary directories:

```python
def test_init_creates_project(runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(cli_group, ["init", "my-app"])
    assert result.exit_code == 0
    assert (tmp_path / "my-app" / "app" / "main.py").is_file()
```

### Template Tests

Template tests render Jinja2 templates with `EntityDefinition` objects and verify the output is valid Python via `ast.parse()`:

```python
def test_model_renders_valid_python(jinja_env, entity):
    output = jinja_env.get_template("model.py.j2").render(entity=entity)
    ast.parse(output)  # Raises SyntaxError if invalid
```

## Testing Generated Projects

After scaffolding a project, you can run its generated tests:

```bash
# Scaffold
poetry run faststack init my-project --entities examples/rag_modulo.yaml

# Run generated unit tests (100 tests for 20 entities)
PYTHONPATH=$(pwd):$(pwd)/my-project poetry run pytest my-project/tests/unit/

# Run generated integration tests (60 tests for 20 entities)
PYTHONPATH=$(pwd):$(pwd)/my-project poetry run pytest my-project/tests/integration/
```

The `PYTHONPATH` workaround is needed because `faststack` isn't published to PyPI yet. In a real project, `poetry install` inside the generated project would handle this.

## Pre-commit Hooks

Pre-commit runs automatically on `git commit`. To run manually:

```bash
make pre-commit          # Run all hooks on all files
make pre-commit-install  # (Re)install hooks into .git/hooks
```

Hooks: trailing whitespace, end-of-file, YAML/TOML validation, Python AST check, debug statement detection, private key detection, ruff lint, black formatting.
