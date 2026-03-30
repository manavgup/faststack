"""Tests for faststack migrate command."""

from click.testing import CliRunner

from cli import cli_group
from cli.cmd_migrate import migrate


class TestMigrateGroup:
    """Tests for the migrate command group."""

    def test_migrate_group_exists(self) -> None:
        """The migrate group is registered on the CLI."""
        command = cli_group.commands.get("migrate")
        assert command is not None

    def test_migrate_has_three_subcommands(self) -> None:
        """The migrate group exposes generate, upgrade, and downgrade."""
        subcommands = set(migrate.commands.keys())
        assert subcommands == {"generate", "upgrade", "downgrade"}


class TestMigrateGenerate:
    """Tests for 'migrate generate'."""

    def test_generate_no_alembic_ini(self, tmp_path, monkeypatch) -> None:
        """Should fail when alembic.ini is missing."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli_group, ["migrate", "generate", "add users table"])
        assert result.exit_code != 0
        assert "No alembic.ini found" in result.output


class TestMigrateUpgrade:
    """Tests for 'migrate upgrade'."""

    def test_upgrade_no_alembic_ini(self, tmp_path, monkeypatch) -> None:
        """Should fail when alembic.ini is missing."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli_group, ["migrate", "upgrade"])
        assert result.exit_code != 0
        assert "No alembic.ini found" in result.output


class TestMigrateDowngrade:
    """Tests for 'migrate downgrade'."""

    def test_downgrade_no_alembic_ini(self, tmp_path, monkeypatch) -> None:
        """Should fail when alembic.ini is missing."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli_group, ["migrate", "downgrade"])
        assert result.exit_code != 0
        assert "No alembic.ini found" in result.output
