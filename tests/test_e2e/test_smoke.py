"""End-to-end smoke test: scaffold a project and validate all generated code.

Covers issue #13: generated project validation.
When Phase 6 entity CLI commands land, this test should be extended to cover
the full init → add-entity → generate → list workflow.
"""

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
def entities_yaml(tmp_path: Path) -> Path:
    """Write a multi-entity YAML fixture."""
    content = """\
entities:
  User:
    base: FullAuditedEntity
    fields:
      email:
        type: string
        required: true
        unique: true
      name:
        type: string
        required: true
      role:
        type: enum
        values: [admin, editor, viewer]
        default: '"viewer"'
    searchable: [email, name]

  Post:
    base: AuditedEntity
    fields:
      title:
        type: string
        required: true
      content:
        type: text
      user_id:
        type: uuid
        references: User
    searchable: [title]

  Category:
    base: AuditedEntity
    fields:
      name:
        type: string
        required: true
      parent_id:
        type: uuid
        references: self
"""
    yaml_file = tmp_path / "entities.yaml"
    yaml_file.write_text(content)
    return yaml_file


class TestProjectScaffoldSmoke:
    """Scaffold a full project and validate the structure."""

    def test_init_succeeds(self, runner: CliRunner, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(cli_group, ["init", "blog"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "Created project" in result.output

    def test_all_expected_directories_exist(
        self, runner: CliRunner, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli_group, ["init", "blog"], catch_exceptions=False)
        project = tmp_path / "blog"

        expected_dirs = [
            "app/models",
            "app/schemas",
            "app/repositories",
            "app/services",
            "app/api/routes",
            "tests/unit/fakes",
            "tests/integration",
            "tests/factories",
            "alembic/versions",
        ]
        for d in expected_dirs:
            assert (project / d).is_dir(), f"Missing directory: {d}"

    def test_project_files_exist(self, runner: CliRunner, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli_group, ["init", "blog"], catch_exceptions=False)
        project = tmp_path / "blog"

        expected_files = [
            "app/main.py",
            "app/config.py",
            "pyproject.toml",
            "Dockerfile",
            "docker-compose.yml",
            "alembic.ini",
            "alembic/env.py",
            "tests/conftest.py",
            ".project-config.yaml",
            ".env",
        ]
        for f in expected_files:
            assert (project / f).is_file(), f"Missing: {f}"

    def test_all_generated_python_is_valid(
        self, runner: CliRunner, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli_group, ["init", "blog"], catch_exceptions=False)
        project = tmp_path / "blog"

        py_files = list(project.rglob("*.py"))
        assert len(py_files) >= 15, f"Expected >=15 .py files, got {len(py_files)}"

        for py_file in py_files:
            source = py_file.read_text()
            if not source.strip():
                continue  # skip empty __init__.py
            try:
                ast.parse(source)
            except SyntaxError as e:
                rel = py_file.relative_to(project)
                pytest.fail(f"Invalid Python in {rel}: {e}")

    def test_project_config_has_structure(
        self, runner: CliRunner, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli_group, ["init", "blog"], catch_exceptions=False)

        config = yaml.safe_load((tmp_path / "blog" / ".project-config.yaml").read_text())
        assert config["project_name"] == "blog"
        assert config["architecture"] == "simple"
        assert "entities" in config


class TestInitWithEntitiesSmoke:
    """Scaffold with --entities and validate router registration."""

    def test_init_with_entities_has_routers_in_main(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch,
        entities_yaml: Path,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            cli_group,
            ["init", "blog", "--entities", str(entities_yaml)],
            catch_exceptions=False,
        )
        assert result.exit_code == 0

        main_content = (tmp_path / "blog" / "app" / "main.py").read_text()
        assert "user_router" in main_content
        assert "post_router" in main_content
        assert "category_router" in main_content
        assert "include_router" in main_content
        ast.parse(main_content)
