"""Tests for ``faststack generate`` CLI command."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from cli import cli_group


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def project_with_entity(runner: CliRunner, tmp_path: Path, monkeypatch) -> Path:
    """Scaffold a project and add a Product entity, returning the project dir."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(cli_group, ["init", "test-project"], catch_exceptions=False)
    assert result.exit_code == 0

    project = tmp_path / "test-project"
    monkeypatch.chdir(project)

    result = runner.invoke(
        cli_group,
        ["add-entity", "Product", "--fields", "name:string:required,price:decimal"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    return project


class TestGenerateRegenerates:
    """Test that ``faststack generate`` regenerates derived files."""

    def test_regenerates_schema(self, runner: CliRunner, project_with_entity: Path) -> None:
        project = project_with_entity
        schema_path = project / "app/schemas/product.py"

        # Record original content
        original_content = schema_path.read_text()
        assert "ProductCreate" in original_content

        # Modify the schema file to simulate drift
        schema_path.write_text("# corrupted\n")

        # Regenerate
        result = runner.invoke(
            cli_group,
            ["generate", "Product"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "Regenerated" in result.output

        # Schema should be restored
        restored_content = schema_path.read_text()
        assert "ProductCreate" in restored_content

    def test_skips_preserved_files(self, runner: CliRunner, project_with_entity: Path) -> None:
        project = project_with_entity

        # Add a custom comment to the service file (PRESERVED)
        service_path = project / "app/services/product.py"
        original = service_path.read_text()
        service_path.write_text("# MY CUSTOM CODE\n" + original)

        result = runner.invoke(
            cli_group,
            ["generate", "Product"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "Skipping" in result.output
        assert "PRESERVED" in result.output

        # Custom comment should still be there
        content = service_path.read_text()
        assert "MY CUSTOM CODE" in content

    def test_updates_hash_in_config(self, runner: CliRunner, project_with_entity: Path) -> None:
        project = project_with_entity

        # Read original hash
        config = yaml.safe_load((project / ".project-config.yaml").read_text())
        original_hash = config["entities"]["Product"]["hash"]

        # Modify model to change hash
        model_path = project / "app/models/product.py"
        model_content = model_path.read_text()
        model_path.write_text(model_content + "\n# modified\n")

        # Regenerate
        runner.invoke(
            cli_group,
            ["generate", "Product"],
            catch_exceptions=False,
        )

        # Hash should be updated
        config = yaml.safe_load((project / ".project-config.yaml").read_text())
        new_hash = config["entities"]["Product"]["hash"]
        assert new_hash != original_hash

    def test_regenerates_all_regeneratable_files(
        self, runner: CliRunner, project_with_entity: Path
    ) -> None:
        project = project_with_entity

        regeneratable = [
            "app/schemas/product.py",
            "tests/unit/fakes/product_repository.py",
            "tests/factories/product.py",
        ]

        # Corrupt all regeneratable files
        for f in regeneratable:
            (project / f).write_text("# corrupted\n")

        # Regenerate
        result = runner.invoke(
            cli_group,
            ["generate", "Product"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # All should be restored
        for f in regeneratable:
            content = (project / f).read_text()
            assert content != "# corrupted\n", f"File {f} was not regenerated"


class TestGenerateRegistryFiles:
    """Test that ``faststack generate`` regenerates registry files."""

    def test_regenerates_dependencies_py(
        self, runner: CliRunner, project_with_entity: Path
    ) -> None:
        project = project_with_entity
        deps_path = project / "app/api/dependencies.py"

        # Corrupt dependencies.py
        deps_path.write_text("# corrupted\n")

        # Regenerate
        result = runner.invoke(
            cli_group,
            ["generate", "Product"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        content = deps_path.read_text()
        assert "get_product_service" in content
        assert "get_db_session" in content

    def test_regenerates_integration_conftest(
        self, runner: CliRunner, project_with_entity: Path
    ) -> None:
        project = project_with_entity
        conftest_path = project / "tests/integration/conftest.py"

        # Corrupt conftest
        conftest_path.write_text("# corrupted\n")

        # Regenerate
        result = runner.invoke(
            cli_group,
            ["generate", "Product"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        content = conftest_path.read_text()
        assert "async def client" in content
        assert "FakeProductRepository" in content


class TestGenerateAllFlag:
    """Test ``faststack generate --all``."""

    def test_generate_all_regenerates_all_entities(
        self, runner: CliRunner, project_with_entity: Path
    ) -> None:
        project = project_with_entity

        # Add a second entity
        runner.invoke(
            cli_group,
            ["add-entity", "Order", "--fields", "total:decimal:required"],
            catch_exceptions=False,
        )

        # Corrupt both schema files
        (project / "app/schemas/product.py").write_text("# corrupted\n")
        (project / "app/schemas/order.py").write_text("# corrupted\n")

        # Regenerate all
        result = runner.invoke(
            cli_group,
            ["generate", "--all"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # Both should be restored
        assert "ProductCreate" in (project / "app/schemas/product.py").read_text()
        assert "OrderCreate" in (project / "app/schemas/order.py").read_text()


class TestGenerateErrorCases:
    """Test error handling in ``faststack generate``."""

    def test_error_no_project_config(self, runner: CliRunner, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            cli_group,
            ["generate", "Product"],
        )

        assert result.exit_code != 0
        assert ".project-config.yaml" in result.output

    def test_error_no_entity_name_or_all(
        self, runner: CliRunner, project_with_entity: Path
    ) -> None:
        result = runner.invoke(
            cli_group,
            ["generate"],
        )

        assert result.exit_code != 0
        assert "Provide entity name or --all" in result.output

    def test_skips_when_model_file_missing(
        self, runner: CliRunner, project_with_entity: Path
    ) -> None:
        project = project_with_entity

        # Remove model file
        (project / "app/models/product.py").unlink()

        result = runner.invoke(
            cli_group,
            ["generate", "Product"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "Skipping Product" in result.output
        assert "model file not found" in result.output
