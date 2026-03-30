"""Tests for ``faststack init`` CLI command."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from click.testing import CliRunner

from cli import cli_group


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def sample_entities_yaml(tmp_path: Path) -> Path:
    """Write a minimal entities.yaml and return its path."""
    yaml_content = """\
entities:
  User:
    base: FullAuditedEntity
    fields:
      name:
        type: string
        required: true
      email:
        type: string
        required: true
        unique: true
    searchable:
      - name
      - email

  Post:
    fields:
      title:
        type: string
        required: true
      user_id:
        type: uuid
        references: User
"""
    yaml_file = tmp_path / "entities.yaml"
    yaml_file.write_text(yaml_content)
    return yaml_file


class TestInitScaffolding:
    """Test that ``faststack init`` creates the expected directory structure."""

    def test_creates_all_expected_directories(self, runner: CliRunner, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(cli_group, ["init", "my-project"], catch_exceptions=False)

        assert result.exit_code == 0

        project = tmp_path / "my-project"
        expected_dirs = [
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
        for d in expected_dirs:
            assert (project / d).is_dir(), f"Missing directory: {d}"

    def test_creates_all_expected_files(self, runner: CliRunner, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(cli_group, ["init", "my-project"], catch_exceptions=False)

        assert result.exit_code == 0

        project = tmp_path / "my-project"
        expected_files = [
            "pyproject.toml",
            "app/main.py",
            "app/config.py",
            "tests/conftest.py",
            "Dockerfile",
            "docker-compose.yml",
            "alembic.ini",
            "alembic/env.py",
            ".project-config.yaml",
            ".env",
        ]
        for f in expected_files:
            assert (project / f).is_file(), f"Missing file: {f}"

    def test_creates_init_py_files(self, runner: CliRunner, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli_group, ["init", "my-project"], catch_exceptions=False)

        project = tmp_path / "my-project"
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
            assert (project / d / "__init__.py").is_file(), f"Missing __init__.py in {d}"


class TestGeneratedFilesAreSyntacticallyValid:
    """Verify that all generated Python files parse without syntax errors."""

    def test_main_py_parses(self, runner: CliRunner, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli_group, ["init", "test-project"], catch_exceptions=False)

        source = (tmp_path / "test-project" / "app" / "main.py").read_text()
        ast.parse(source)

    def test_config_py_parses(self, runner: CliRunner, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli_group, ["init", "test-project"], catch_exceptions=False)

        source = (tmp_path / "test-project" / "app" / "config.py").read_text()
        ast.parse(source)

    def test_conftest_py_parses(self, runner: CliRunner, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli_group, ["init", "test-project"], catch_exceptions=False)

        source = (tmp_path / "test-project" / "tests" / "conftest.py").read_text()
        ast.parse(source)

    def test_alembic_env_py_parses(self, runner: CliRunner, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli_group, ["init", "test-project"], catch_exceptions=False)

        source = (tmp_path / "test-project" / "alembic" / "env.py").read_text()
        ast.parse(source)


class TestFileContents:
    """Verify key content expectations in generated files."""

    def test_pyproject_contains_project_name(self, runner: CliRunner, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli_group, ["init", "cool-app"], catch_exceptions=False)

        content = (tmp_path / "cool-app" / "pyproject.toml").read_text()
        assert 'name = "cool-app"' in content

    def test_main_py_imports_faststack_core(self, runner: CliRunner, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli_group, ["init", "cool-app"], catch_exceptions=False)

        content = (tmp_path / "cool-app" / "app" / "main.py").read_text()
        assert "from faststack_core" in content
        assert "setup_app" in content

    def test_alembic_env_uses_async_engine(self, runner: CliRunner, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli_group, ["init", "cool-app"], catch_exceptions=False)

        content = (tmp_path / "cool-app" / "alembic" / "env.py").read_text()
        assert "create_async_engine" in content
        assert "run_sync" in content

    def test_conftest_has_async_fixtures(self, runner: CliRunner, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli_group, ["init", "cool-app"], catch_exceptions=False)

        content = (tmp_path / "cool-app" / "tests" / "conftest.py").read_text()
        assert "async def async_engine" in content
        assert "async def session" in content
        assert "@pytest.fixture" in content

    def test_project_config_yaml_exists(self, runner: CliRunner, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli_group, ["init", "cool-app"], catch_exceptions=False)

        content = (tmp_path / "cool-app" / ".project-config.yaml").read_text()
        assert "project_name: cool-app" in content

    def test_docker_compose_contains_project_name(
        self, runner: CliRunner, tmp_path: Path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli_group, ["init", "cool-app"], catch_exceptions=False)

        content = (tmp_path / "cool-app" / "docker-compose.yml").read_text()
        assert "cool_app" in content  # project_name | lower | replace('-', '_')


class TestWithEntitiesFlag:
    """Test ``faststack init`` with the ``--entities`` flag."""

    def test_entity_routers_in_main_py(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch,
        sample_entities_yaml: Path,
    ):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            cli_group,
            ["init", "entity-project", "--entities", str(sample_entities_yaml)],
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        content = (tmp_path / "entity-project" / "app" / "main.py").read_text()
        assert "user_router" in content
        assert "post_router" in content
        assert "include_router" in content

    def test_next_steps_include_migrate(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch,
        sample_entities_yaml: Path,
    ):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            cli_group,
            ["init", "entity-project", "--entities", str(sample_entities_yaml)],
            catch_exceptions=False,
        )

        assert "faststack migrate" in result.output


class TestErrorCases:
    """Test error handling in ``faststack init``."""

    def test_error_when_directory_already_exists(
        self, runner: CliRunner, tmp_path: Path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "existing-project").mkdir()

        result = runner.invoke(cli_group, ["init", "existing-project"])

        assert result.exit_code != 0
        assert "already exists" in result.output
