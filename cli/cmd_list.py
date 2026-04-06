"""faststack list — show entity generation status."""

import hashlib
from pathlib import Path

import click
import yaml

from cli import cli_group


@cli_group.command("list")
def list_entities() -> None:
    """Show all entities and their generation status."""
    config_path = Path(".project-config.yaml")
    if not config_path.exists():
        raise click.ClickException("No .project-config.yaml found. Run this from a FastStack project root.")

    config = yaml.safe_load(config_path.read_text())
    entities = config.get("entities", {})

    if not entities:
        click.echo("No entities registered. Run 'faststack add-entity' to create one.")
        return

    # Header
    click.echo(f"{'Entity':<20} {'Model':<40} {'Status':<20}")
    click.echo("-" * 80)

    for entity_name, entity_info in entities.items():
        model_path = Path(entity_info.get("model_path", f"app/models/{entity_name.lower()}.py"))
        stored_hash = entity_info.get("hash", "")

        if not model_path.exists():
            status = click.style("MISSING", fg="red")
        else:
            current_hash = _file_hash(model_path)
            if current_hash == stored_hash:
                status = click.style("up to date", fg="green")
            else:
                status = click.style("schemas outdated", fg="yellow")

        click.echo(f"{entity_name:<20} {str(model_path):<40} {status}")


def _file_hash(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()
