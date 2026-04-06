"""faststack migrate — Alembic migration wrapper."""

import subprocess
import sys
from pathlib import Path

import click

from cli import cli_group


@cli_group.group("migrate")
def migrate() -> None:
    """Database migration commands (wraps Alembic)."""


@migrate.command("generate")
@click.argument("message")
def migrate_generate(message: str) -> None:
    """Generate a new migration from model changes."""
    _run_alembic(["revision", "--autogenerate", "-m", message])


@migrate.command("upgrade")
def migrate_upgrade() -> None:
    """Apply all pending migrations."""
    _run_alembic(["upgrade", "head"])


@migrate.command("downgrade")
def migrate_downgrade() -> None:
    """Roll back one migration."""
    _run_alembic(["downgrade", "-1"])


def _run_alembic(args: list[str]) -> None:
    """Run an Alembic command, checking for alembic.ini in cwd."""
    if not Path("alembic.ini").exists():
        raise click.ClickException(
            "No alembic.ini found in current directory. " "Run this command from your project root."
        )
    result = subprocess.run(
        [sys.executable, "-m", "alembic"] + args,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(result.returncode)
