"""FastStack CLI — Click-based entry point for the `faststack` command."""

import click


@click.group()
@click.version_option(version="0.1.0", prog_name="faststack")
def cli() -> None:
    """FastStack — Hybrid FastAPI framework + CLI generator."""
    pass
