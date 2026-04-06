"""Tests for ``faststack add-entity`` CLI command."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from cli import cli_group


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def project_dir(runner: CliRunner, tmp_path: Path, monkeypatch) -> Path:
    """Scaffold a FastStack project and chdir into it."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(cli_group, ["init", "test-project"], catch_exceptions=False)
    assert result.exit_code == 0

    project = tmp_path / "test-project"
    monkeypatch.chdir(project)
    return project


@pytest.fixture
def sample_entities_yaml(tmp_path: Path) -> Path:
    """Write a minimal entities.yaml and return its path."""
    yaml_content = """\
entities:
  Product:
    base: FullAuditedEntity
    fields:
      name:
        type: string
        required: true
      price:
        type: decimal
    searchable:
      - name
"""
    yaml_file = tmp_path / "entities.yaml"
    yaml_file.write_text(yaml_content)
    return yaml_file


class TestAddEntityCreatesFiles:
    """Test that ``faststack add-entity`` creates all 9 entity files."""

    def test_creates_all_entity_files(self, runner: CliRunner, project_dir: Path) -> None:
        result = runner.invoke(
            cli_group,
            ["add-entity", "Product", "--fields", "name:string:required,price:decimal"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "Created entity 'Product'" in result.output

        expected_files = [
            "app/models/product.py",
            "app/schemas/product.py",
            "app/repositories/product.py",
            "app/services/product.py",
            "app/api/routes/product.py",
            "tests/factories/product.py",
            "tests/unit/fakes/product_repository.py",
            "tests/unit/test_product_service.py",
            "tests/integration/test_product_api.py",
        ]
        for f in expected_files:
            assert (project_dir / f).is_file(), f"Missing file: {f}"

    def test_updates_project_config(self, runner: CliRunner, project_dir: Path) -> None:
        runner.invoke(
            cli_group,
            ["add-entity", "Product", "--fields", "name:string:required,price:decimal"],
            catch_exceptions=False,
        )

        config = yaml.safe_load((project_dir / ".project-config.yaml").read_text())
        assert "Product" in config["entities"]
        assert "hash" in config["entities"]["Product"]
        assert "model_path" in config["entities"]["Product"]
        assert config["entities"]["Product"]["hash"] != ""

    def test_generated_model_is_valid_python(self, runner: CliRunner, project_dir: Path) -> None:
        runner.invoke(
            cli_group,
            ["add-entity", "Product", "--fields", "name:string:required,price:decimal"],
            catch_exceptions=False,
        )

        source = (project_dir / "app/models/product.py").read_text()
        ast.parse(source)  # raises SyntaxError if invalid

    def test_generated_schema_is_valid_python(self, runner: CliRunner, project_dir: Path) -> None:
        runner.invoke(
            cli_group,
            ["add-entity", "Product", "--fields", "name:string:required,price:decimal"],
            catch_exceptions=False,
        )

        source = (project_dir / "app/schemas/product.py").read_text()
        ast.parse(source)

    def test_generated_service_is_valid_python(self, runner: CliRunner, project_dir: Path) -> None:
        runner.invoke(
            cli_group,
            ["add-entity", "Product", "--fields", "name:string:required,price:decimal"],
            catch_exceptions=False,
        )

        source = (project_dir / "app/services/product.py").read_text()
        ast.parse(source)


class TestAddEntityFromYaml:
    """Test ``faststack add-entity --from-yaml``."""

    def test_from_yaml_creates_entity(
        self,
        runner: CliRunner,
        project_dir: Path,
        sample_entities_yaml: Path,
    ) -> None:
        result = runner.invoke(
            cli_group,
            ["add-entity", "Product", "--from-yaml", str(sample_entities_yaml)],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert (project_dir / "app/models/product.py").is_file()

        # Check model file references the entity name
        model_content = (project_dir / "app/models/product.py").read_text()
        assert "class Product" in model_content

    def test_from_yaml_entity_not_found(
        self,
        runner: CliRunner,
        project_dir: Path,
        sample_entities_yaml: Path,
    ) -> None:
        result = runner.invoke(
            cli_group,
            ["add-entity", "NonExistent", "--from-yaml", str(sample_entities_yaml)],
        )

        assert result.exit_code != 0
        assert "not found" in result.output


class TestAddEntityErrorCases:
    """Test error handling in ``faststack add-entity``."""

    def test_error_entity_already_exists(self, runner: CliRunner, project_dir: Path) -> None:
        # First creation succeeds
        result1 = runner.invoke(
            cli_group,
            ["add-entity", "Product", "--fields", "name:string:required"],
            catch_exceptions=False,
        )
        assert result1.exit_code == 0

        # Second creation without --update fails
        result2 = runner.invoke(
            cli_group,
            ["add-entity", "Product", "--fields", "name:string:required"],
        )
        assert result2.exit_code != 0
        assert "already exists" in result2.output

    def test_update_flag_succeeds_when_entity_exists(self, runner: CliRunner, project_dir: Path) -> None:
        # First creation
        runner.invoke(
            cli_group,
            ["add-entity", "Product", "--fields", "name:string:required"],
            catch_exceptions=False,
        )

        # Update with new fields
        result = runner.invoke(
            cli_group,
            [
                "add-entity",
                "Product",
                "--fields",
                "name:string:required,price:decimal",
                "--update",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "Updated entity 'Product'" in result.output

        # Model file should now contain price field
        model_content = (project_dir / "app/models/product.py").read_text()
        assert "price" in model_content

    def test_error_no_project_config(self, runner: CliRunner, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            cli_group,
            ["add-entity", "Product", "--fields", "name:string:required"],
        )

        assert result.exit_code != 0
        assert ".project-config.yaml" in result.output

    def test_error_no_fields_or_yaml(self, runner: CliRunner, project_dir: Path) -> None:
        result = runner.invoke(
            cli_group,
            ["add-entity", "Product"],
        )

        assert result.exit_code != 0
        assert "Provide --fields or --from-yaml" in result.output


class TestAddEntityRegistration:
    """Test that ``faststack add-entity`` registers the router in main.py and generates registry files."""

    def test_registers_router_in_main_py(self, runner: CliRunner, project_dir: Path) -> None:
        runner.invoke(
            cli_group,
            ["add-entity", "Product", "--fields", "name:string:required,price:decimal"],
            catch_exceptions=False,
        )

        main_content = (project_dir / "app/main.py").read_text()
        assert "from app.api.routes.product import router as product_router" in main_content
        assert "app.include_router(product_router" in main_content

    def test_no_duplicate_router_registration(self, runner: CliRunner, project_dir: Path) -> None:
        # First creation
        runner.invoke(
            cli_group,
            ["add-entity", "Product", "--fields", "name:string:required"],
            catch_exceptions=False,
        )

        # Update with --update (should not duplicate)
        runner.invoke(
            cli_group,
            ["add-entity", "Product", "--fields", "name:string:required,price:decimal", "--update"],
            catch_exceptions=False,
        )

        main_content = (project_dir / "app/main.py").read_text()
        assert main_content.count("product_router") == 2  # one import, one include_router

    def test_generates_dependencies_py(self, runner: CliRunner, project_dir: Path) -> None:
        runner.invoke(
            cli_group,
            ["add-entity", "Product", "--fields", "name:string:required"],
            catch_exceptions=False,
        )

        deps_path = project_dir / "app/api/dependencies.py"
        assert deps_path.is_file()
        content = deps_path.read_text()
        assert "get_product_service" in content
        assert "get_db_session" in content
        ast.parse(content)

    def test_generates_integration_conftest(self, runner: CliRunner, project_dir: Path) -> None:
        runner.invoke(
            cli_group,
            ["add-entity", "Product", "--fields", "name:string:required"],
            catch_exceptions=False,
        )

        conftest_path = project_dir / "tests/integration/conftest.py"
        assert conftest_path.is_file()
        content = conftest_path.read_text()
        assert "async def client" in content
        assert "FakeProductRepository" in content
        ast.parse(content)

    def test_multiple_entities_in_registry_files(self, runner: CliRunner, project_dir: Path) -> None:
        runner.invoke(
            cli_group,
            ["add-entity", "Product", "--fields", "name:string:required"],
            catch_exceptions=False,
        )
        runner.invoke(
            cli_group,
            ["add-entity", "Order", "--fields", "total:decimal:required"],
            catch_exceptions=False,
        )

        deps_content = (project_dir / "app/api/dependencies.py").read_text()
        assert "get_product_service" in deps_content
        assert "get_order_service" in deps_content
        ast.parse(deps_content)

        conftest_content = (project_dir / "tests/integration/conftest.py").read_text()
        assert "FakeProductRepository" in conftest_content
        assert "FakeOrderRepository" in conftest_content
        ast.parse(conftest_content)


class TestAddEntityFileContents:
    """Test content of generated entity files."""

    def test_model_contains_class_and_tablename(self, runner: CliRunner, project_dir: Path) -> None:
        runner.invoke(
            cli_group,
            ["add-entity", "Product", "--fields", "name:string:required,price:decimal"],
            catch_exceptions=False,
        )

        content = (project_dir / "app/models/product.py").read_text()
        assert "class Product(" in content
        assert '__tablename__ = "products"' in content

    def test_schema_contains_create_and_response(self, runner: CliRunner, project_dir: Path) -> None:
        runner.invoke(
            cli_group,
            ["add-entity", "Product", "--fields", "name:string:required,price:decimal"],
            catch_exceptions=False,
        )

        content = (project_dir / "app/schemas/product.py").read_text()
        assert "class ProductCreate(" in content
        assert "class ProductUpdate(" in content
        assert "class ProductResponse(" in content
        assert "class ProductDetailResponse(" in content

    def test_repository_references_entity(self, runner: CliRunner, project_dir: Path) -> None:
        runner.invoke(
            cli_group,
            ["add-entity", "Product", "--fields", "name:string:required"],
            catch_exceptions=False,
        )

        content = (project_dir / "app/repositories/product.py").read_text()
        assert "class ProductRepository(" in content
        assert "from app.models.product import Product" in content

    def test_next_steps_message(self, runner: CliRunner, project_dir: Path) -> None:
        result = runner.invoke(
            cli_group,
            ["add-entity", "Product", "--fields", "name:string:required"],
            catch_exceptions=False,
        )

        assert "faststack migrate generate" in result.output
