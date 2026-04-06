"""faststack init — scaffold a new FastStack project."""

import os
from pathlib import Path

import click
from jinja2 import Environment, FileSystemLoader

from cli import cli_group
from cli.cmd_add_entity import (
    _camel_to_snake,
    _generate_entity_files,
    _pluralize,
    _regenerate_registry_files,
    _update_project_config,
)
from cli.yaml_parser import parse_entities_yaml

TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "project"


@cli_group.command("init")
@click.argument("project_name")
@click.option("--entities", type=click.Path(exists=True), help="Path to entities.yaml")
def init_project(project_name: str, entities: str | None = None) -> None:
    """Scaffold a new FastStack project."""

    project_dir = Path.cwd() / project_name
    if project_dir.exists():
        raise click.ClickException(f"Directory '{project_name}' already exists")

    # Parse entities if YAML provided
    entity_defs = []
    if entities:
        entity_defs = parse_entities_yaml(Path(entities))

    # Create directory structure
    dirs = [
        "app",
        "app/models",
        "app/schemas",
        "app/repositories",
        "app/services",
        "app/api",
        "app/api/routes",
        "alembic",
        "alembic/versions",
        "tests",
        "tests/unit",
        "tests/unit/fakes",
        "tests/integration",
        "tests/factories",
    ]
    for d in dirs:
        (project_dir / d).mkdir(parents=True, exist_ok=True)

    # Create __init__.py files
    init_dirs = [
        "app",
        "app/models",
        "app/schemas",
        "app/repositories",
        "app/services",
        "app/api",
        "app/api/routes",
        "tests",
        "tests/unit",
        "tests/unit/fakes",
        "tests/integration",
        "tests/factories",
    ]
    for d in init_dirs:
        (project_dir / d / "__init__.py").write_text("")

    # Render templates
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), keep_trailing_newline=True)
    env.filters["snake_case"] = _camel_to_snake
    env.filters["pluralize"] = _pluralize

    template_context = {
        "project_name": project_name,
        "entities": entity_defs,
    }

    file_mappings = {
        "pyproject.toml.j2": "pyproject.toml",
        "main.py.j2": "app/main.py",
        "config.py.j2": "app/config.py",
        "conftest.py.j2": "tests/conftest.py",
        "Dockerfile.j2": "Dockerfile",
        "docker-compose.yml.j2": "docker-compose.yml",
        "alembic.ini.j2": "alembic.ini",
        "alembic_env.py.j2": "alembic/env.py",
    }

    for template_name, output_path in file_mappings.items():
        template = env.get_template(template_name)
        content = template.render(**template_context)
        (project_dir / output_path).write_text(content)

    # Create .project-config.yaml
    config_content = f"project_name: {project_name}\narchitecture: simple\nentities: {{}}\n"
    (project_dir / ".project-config.yaml").write_text(config_content)

    # Create .env file
    db_name = project_name.lower().replace("-", "_")
    env_content = f"DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/{db_name}\n" f"LOG_LEVEL=INFO\n"
    (project_dir / ".env").write_text(env_content)

    # Generate entity files if YAML was provided
    if entity_defs:
        original_cwd = os.getcwd()
        os.chdir(project_dir)
        try:
            config_path = Path(".project-config.yaml")
            for entity_def in entity_defs:
                _generate_entity_files(entity_def, update=False)
                model_path = Path(f"app/models/{_camel_to_snake(entity_def.name)}.py")
                _update_project_config(config_path, entity_def, model_path)
                click.echo(f"  Generated entity: {entity_def.name}")
            _regenerate_registry_files()
        finally:
            os.chdir(original_cwd)

    click.echo(f"\nCreated project '{project_name}' at {project_dir}")
    if entity_defs:
        click.echo(f"  {len(entity_defs)} entities generated")
    click.echo()
    click.echo("Next steps:")
    click.echo(f"  cd {project_name}")
    click.echo("  poetry install")
    if entity_defs:
        click.echo('  faststack migrate generate "initial"')
        click.echo("  faststack migrate upgrade")
    else:
        click.echo("  faststack add-entity YourEntity --fields 'name:string:required'")
