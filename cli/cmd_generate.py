"""faststack generate — regenerate derived files from models."""

import hashlib
from pathlib import Path

import click
import yaml
from jinja2 import Environment, FileSystemLoader

from cli import cli_group
from cli.model_introspector import introspect_model

SIMPLE_TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "simple"

REGENERATABLE_FILES = {
    "schema.py.j2": "app/schemas/{name}.py",
    "fake_repository.py.j2": "tests/unit/fakes/{name}_repository.py",
    "factory.py.j2": "tests/factories/{name}.py",
}

PRESERVED_FILES = {
    "model.py.j2": "app/models/{name}.py",
    "repository.py.j2": "app/repositories/{name}.py",
    "service.py.j2": "app/services/{name}.py",
    "router.py.j2": "app/api/routes/{name}.py",
    "test_unit_service.py.j2": "tests/unit/test_{name}_service.py",
    "test_integration.py.j2": "tests/integration/test_{name}_api.py",
}


@cli_group.command("generate")
@click.argument("entity_name", required=False)
@click.option("--all", "generate_all", is_flag=True, help="Regenerate all entities")
@click.option("--force", is_flag=True, help="Also regenerate PRESERVED files (with confirmation)")
def generate(entity_name: str | None, generate_all: bool, force: bool) -> None:
    """Regenerate derived files from model (schemas, fakes, factories)."""
    config_path = Path(".project-config.yaml")
    if not config_path.exists():
        raise click.ClickException("No .project-config.yaml found.")

    config = yaml.safe_load(config_path.read_text()) or {}
    entities = config.get("entities", {})
    if entities is None:
        entities = {}

    if generate_all:
        names = list(entities.keys())
    elif entity_name:
        names = [entity_name]
    else:
        raise click.ClickException("Provide entity name or --all")

    for name in names:
        model_path = Path(f"app/models/{name.lower()}.py")
        if not model_path.exists():
            click.echo(f"Skipping {name}: model file not found at {model_path}")
            continue

        # Introspect model
        entity_def = introspect_model(model_path)

        # Render REGENERATABLE files
        env = Environment(
            loader=FileSystemLoader(str(SIMPLE_TEMPLATE_DIR)),
            keep_trailing_newline=True,
        )

        for template_name, path_pattern in REGENERATABLE_FILES.items():
            output_path = Path(path_pattern.format(name=name.lower()))
            template = env.get_template(template_name)
            content = template.render(entity=entity_def)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content)
            click.echo(f"  Regenerated {output_path}")

        # Skip PRESERVED files unless --force
        if force:
            if not click.confirm(
                f"Regenerate PRESERVED files for {name}? This will overwrite user code."
            ):
                continue
            for template_name, path_pattern in PRESERVED_FILES.items():
                output_path = Path(path_pattern.format(name=name.lower()))
                template = env.get_template(template_name)
                content = template.render(entity=entity_def)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(content)
                click.echo(f"  Regenerated (PRESERVED) {output_path}")
        else:
            for path_pattern in PRESERVED_FILES.values():
                output_path = Path(path_pattern.format(name=name.lower()))
                if output_path.exists():
                    click.echo(f"  Skipping {output_path} (PRESERVED — contains user code)")

        # Update hash
        new_hash = hashlib.sha256(model_path.read_bytes()).hexdigest()
        entities[name] = entities.get(name, {}) or {}
        entities[name]["hash"] = new_hash
        entities[name]["model_path"] = str(model_path)

    config["entities"] = entities
    config_path.write_text(yaml.dump(config, default_flow_style=False))
    click.echo("\nDone.")
