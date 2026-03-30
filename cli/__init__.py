"""FastStack CLI — Click-based entry point for the `faststack` command."""

import click


@click.group()
@click.version_option(version="0.1.0", prog_name="faststack")
def cli() -> None:
    """FastStack — Hybrid FastAPI framework + CLI generator."""


# Alias so submodules can import the Click group without name collision
# with the ``cli`` package itself.
cli_group = cli


def _register_commands() -> None:
    """Import subcommands to register them with the CLI group."""
    import cli.cmd_init  # noqa: F401


_register_commands()
