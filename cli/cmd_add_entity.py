"""faststack add-entity — scaffold a new entity."""

import ast
import hashlib
from pathlib import Path

import click
import inflect
import yaml
from jinja2 import Environment, FileSystemLoader

from cli import cli_group
from cli.yaml_parser import EntityDefinition, FieldDefinition, parse_entities_yaml

SIMPLE_TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "simple"

_inflect_engine = inflect.engine()

# Templates that are safe to regenerate (no user code expected)
REGENERATABLE_TEMPLATES = {
    "schema.py.j2": "app/schemas/{name}.py",
    "fake_repository.py.j2": "tests/unit/fakes/{name}_repository.py",
    "factory.py.j2": "tests/factories/{name}.py",
}

# Templates that may contain user code and should not be overwritten
PRESERVED_TEMPLATES = {
    "model.py.j2": "app/models/{name}.py",
    "repository.py.j2": "app/repositories/{name}.py",
    "service.py.j2": "app/services/{name}.py",
    "router.py.j2": "app/api/routes/{name}.py",
    "test_unit_service.py.j2": "tests/unit/test_{name}_service.py",
    "test_integration.py.j2": "tests/integration/test_{name}_api.py",
}


def _camel_to_snake(name: str) -> str:
    """Convert ``CamelCase`` to ``snake_case``."""
    import re

    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _pluralize(name: str) -> str:
    """Return a lowercase, pluralized table name for *name*."""
    snake = _camel_to_snake(name)
    plural = _inflect_engine.plural_noun(snake)
    return plural if plural else snake


def _parse_fields_flag(name: str, fields_str: str) -> EntityDefinition:
    """Parse ``"name:type:required,price:decimal"`` into an EntityDefinition."""
    fields: list[FieldDefinition] = []
    for part in fields_str.split(","):
        parts = part.strip().split(":")
        if not parts or not parts[0]:
            continue
        field_name = parts[0].strip()
        field_type = parts[1].strip() if len(parts) > 1 else "string"
        required = len(parts) > 2 and parts[2].strip().lower() == "required"
        fields.append(
            FieldDefinition(
                name=field_name,
                type=field_type,
                required=required,
            )
        )

    return EntityDefinition(
        name=name,
        table_name=_pluralize(name),
        fields=fields,
    )


def _generate_entity_files(entity_def: EntityDefinition, update: bool) -> None:
    """Render all 9 entity templates and write to the correct locations."""
    env = Environment(
        loader=FileSystemLoader(str(SIMPLE_TEMPLATE_DIR)),
        keep_trailing_newline=True,
    )
    env.filters["snake_case"] = _camel_to_snake
    env.filters["pluralize"] = _pluralize

    name_snake = _camel_to_snake(entity_def.name)

    # Always write REGENERATABLE files
    for template_name, path_pattern in REGENERATABLE_TEMPLATES.items():
        output_path = Path(path_pattern.format(name=name_snake))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        template = env.get_template(template_name)
        content = template.render(entity=entity_def)
        output_path.write_text(content)

    # PRESERVED files: only write if file doesn't exist, or if --update
    for template_name, path_pattern in PRESERVED_TEMPLATES.items():
        output_path = Path(path_pattern.format(name=name_snake))
        if output_path.exists() and not update:
            continue
        output_path.parent.mkdir(parents=True, exist_ok=True)
        template = env.get_template(template_name)
        content = template.render(entity=entity_def)
        output_path.write_text(content)


def _register_router_in_main(entity_name: str) -> None:
    """Append router import and include_router to app/main.py if not already present."""
    main_path = Path("app/main.py")
    if not main_path.exists():
        return

    snake = _camel_to_snake(entity_name)
    source = main_path.read_text()

    # Use AST to check whether the import already exists
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return

    module_name = f"app.api.routes.{snake}"
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == module_name:
            return  # already registered

    import_line = f"from app.api.routes.{snake} import router as {snake}_router"
    include_line = f'app.include_router({snake}_router, prefix="/api")'

    lines = source.rstrip("\n").split("\n")

    # Find the last include_router line to insert after it
    last_include_idx = -1
    for i, line in enumerate(lines):
        if "app.include_router(" in line:
            last_include_idx = i

    if last_include_idx >= 0:
        # Insert after the last include_router block
        lines.insert(last_include_idx + 1, f"\n{import_line}")
        lines.insert(last_include_idx + 2, include_line)
    else:
        # No existing include_router — append at end of file
        lines.append("")
        lines.append(import_line)
        lines.append(include_line)

    main_path.write_text("\n".join(lines) + "\n")


def _regenerate_registry_files() -> None:
    """Render multi-entity templates (dependencies.py, integration conftest).

    These templates need the full entity list from .project-config.yaml,
    unlike per-entity templates.
    """
    config_path = Path(".project-config.yaml")
    if not config_path.exists():
        return

    config = yaml.safe_load(config_path.read_text()) or {}
    entities_map = config.get("entities") or {}
    if not entities_map:
        return

    # Build entity context list
    entities = [{"name": name, "snake_name": _camel_to_snake(name)} for name in entities_map]

    env = Environment(
        loader=FileSystemLoader(str(SIMPLE_TEMPLATE_DIR)),
        keep_trailing_newline=True,
    )
    env.filters["snake_case"] = _camel_to_snake
    env.filters["pluralize"] = _pluralize

    context = {"entities": entities}

    # Render dependencies.py
    deps_path = Path("app/api/dependencies.py")
    deps_path.parent.mkdir(parents=True, exist_ok=True)
    deps_template = env.get_template("dependencies.py.j2")
    deps_path.write_text(deps_template.render(**context))

    # Render integration test conftest
    conftest_path = Path("tests/integration/conftest.py")
    conftest_path.parent.mkdir(parents=True, exist_ok=True)
    conftest_template = env.get_template("conftest_integration.py.j2")
    conftest_path.write_text(conftest_template.render(**context))


def _update_project_config(config_path: Path, entity_def: EntityDefinition, model_path: Path) -> None:
    """Update ``.project-config.yaml`` with entity name, model path, and hash."""
    config = yaml.safe_load(config_path.read_text()) or {}
    entities = config.get("entities", {})
    if entities is None:
        entities = {}

    model_hash = ""
    if model_path.exists():
        model_hash = hashlib.sha256(model_path.read_bytes()).hexdigest()

    entities[entity_def.name] = {
        "model_path": str(model_path),
        "hash": model_hash,
    }
    config["entities"] = entities
    config_path.write_text(yaml.dump(config, default_flow_style=False))


@cli_group.command("add-entity")
@click.argument("entity_name")
@click.option("--fields", help='Field definitions: "name:type:required,price:decimal"')
@click.option(
    "--from-yaml",
    "yaml_path",
    type=click.Path(exists=True),
    help="Path to entities.yaml",
)
@click.option("--update", is_flag=True, help="Update existing entity (merge new fields)")
def add_entity(
    entity_name: str,
    fields: str | None,
    yaml_path: str | None,
    update: bool,
) -> None:
    """Add a new entity to the project."""
    # Check we're in a FastStack project
    config_path = Path(".project-config.yaml")
    if not config_path.exists():
        raise click.ClickException("No .project-config.yaml found. Run from project root.")

    # Build EntityDefinition from flags or YAML
    if yaml_path:
        entities = parse_entities_yaml(Path(yaml_path))
        entity_def = next((e for e in entities if e.name == entity_name), None)
        if entity_def is None:
            raise click.ClickException(f"Entity '{entity_name}' not found in {yaml_path}")
    elif fields:
        entity_def = _parse_fields_flag(entity_name, fields)
    else:
        raise click.ClickException("Provide --fields or --from-yaml")

    # Check if entity already exists
    model_path = Path(f"app/models/{_camel_to_snake(entity_name)}.py")
    if model_path.exists() and not update:
        raise click.ClickException(f"Entity '{entity_name}' already exists. Use --update to merge fields.")

    # Generate files from templates
    _generate_entity_files(entity_def, update)

    # Update .project-config.yaml
    _update_project_config(config_path, entity_def, model_path)

    # Register router in main.py and regenerate registry files
    _register_router_in_main(entity_name)
    _regenerate_registry_files()

    click.echo(f"{'Updated' if update else 'Created'} entity '{entity_name}'")
    click.echo(f"\nRun 'faststack migrate generate \"add {entity_name.lower()}\"' " f"to create the migration.")
