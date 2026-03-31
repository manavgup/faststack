"""Tests for project template rendering (without the CLI)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
import yaml
from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates" / "project"


@pytest.fixture
def jinja_env():
    from cli.cmd_add_entity import _camel_to_snake, _pluralize

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), keep_trailing_newline=True)
    env.filters["snake_case"] = _camel_to_snake
    env.filters["pluralize"] = _pluralize
    return env


@pytest.fixture
def base_context():
    """Minimal template context with no entities."""
    return {
        "project_name": "sample-project",
        "entities": [],
    }


@pytest.fixture
def entity_context():
    """Template context with sample entity-like objects."""
    from dataclasses import dataclass

    @dataclass
    class FakeEntity:
        name: str

    return {
        "project_name": "entity-project",
        "entities": [FakeEntity(name="User"), FakeEntity(name="Post")],
    }


class TestPythonTemplatesProduceValidPython:
    """All .py templates must produce syntactically valid Python."""

    def test_main_py(self, jinja_env, base_context):
        content = jinja_env.get_template("main.py.j2").render(**base_context)
        ast.parse(content)

    def test_main_py_with_entities(self, jinja_env, entity_context):
        content = jinja_env.get_template("main.py.j2").render(**entity_context)
        ast.parse(content)

    def test_config_py(self, jinja_env, base_context):
        content = jinja_env.get_template("config.py.j2").render(**base_context)
        ast.parse(content)

    def test_conftest_py(self, jinja_env, base_context):
        content = jinja_env.get_template("conftest.py.j2").render(**base_context)
        ast.parse(content)

    def test_alembic_env_py(self, jinja_env, base_context):
        content = jinja_env.get_template("alembic_env.py.j2").render(**base_context)
        ast.parse(content)


class TestYamlTemplatesProduceValidYaml:
    """YAML templates must produce parsable YAML."""

    def test_docker_compose_yml(self, jinja_env, base_context):
        content = jinja_env.get_template("docker-compose.yml.j2").render(**base_context)
        parsed = yaml.safe_load(content)
        assert "services" in parsed
        assert "db" in parsed["services"]
        assert "app" in parsed["services"]

    def test_docker_compose_uses_project_db_name(self, jinja_env, base_context):
        content = jinja_env.get_template("docker-compose.yml.j2").render(**base_context)
        parsed = yaml.safe_load(content)
        db_env = parsed["services"]["db"]["environment"]
        assert db_env["POSTGRES_DB"] == "sample_project"


class TestDockerfileTemplate:
    """Verify the Dockerfile template produces expected content."""

    def test_has_from_stage(self, jinja_env, base_context):
        content = jinja_env.get_template("Dockerfile.j2").render(**base_context)
        assert content.startswith("FROM python:3.12-slim")

    def test_has_expose(self, jinja_env, base_context):
        content = jinja_env.get_template("Dockerfile.j2").render(**base_context)
        assert "EXPOSE 8000" in content

    def test_has_cmd(self, jinja_env, base_context):
        content = jinja_env.get_template("Dockerfile.j2").render(**base_context)
        assert "CMD" in content
        assert "uvicorn" in content


class TestAlembicIniTemplate:
    """Verify alembic.ini template renders correctly."""

    def test_has_script_location(self, jinja_env, base_context):
        content = jinja_env.get_template("alembic.ini.j2").render(**base_context)
        assert "script_location = alembic" in content

    def test_has_loggers_section(self, jinja_env, base_context):
        content = jinja_env.get_template("alembic.ini.j2").render(**base_context)
        assert "[loggers]" in content


class TestPyprojectTomlTemplate:
    """Verify pyproject.toml template renders correctly."""

    def test_contains_project_name(self, jinja_env, base_context):
        content = jinja_env.get_template("pyproject.toml.j2").render(**base_context)
        assert 'name = "sample-project"' in content

    def test_contains_faststack_dependency(self, jinja_env, base_context):
        content = jinja_env.get_template("pyproject.toml.j2").render(**base_context)
        assert "faststack" in content

    def test_contains_pytest_config(self, jinja_env, base_context):
        content = jinja_env.get_template("pyproject.toml.j2").render(**base_context)
        assert 'asyncio_mode = "auto"' in content


class TestConfigTemplate:
    """Verify config.py template renders with correct DB name."""

    def test_database_url_uses_snake_case_name(self, jinja_env):
        ctx = {"project_name": "my-cool-app", "entities": []}
        content = jinja_env.get_template("config.py.j2").render(**ctx)
        assert "my_cool_app" in content

    def test_has_settings_class(self, jinja_env, base_context):
        content = jinja_env.get_template("config.py.j2").render(**base_context)
        assert "class Settings" in content


class TestMainTemplateWithEntities:
    """Verify main.py template entity router inclusion."""

    def test_includes_entity_routers(self, jinja_env, entity_context):
        content = jinja_env.get_template("main.py.j2").render(**entity_context)
        assert "user_router" in content
        assert "post_router" in content
        assert "include_router" in content

    def test_no_routers_without_entities(self, jinja_env, base_context):
        content = jinja_env.get_template("main.py.j2").render(**base_context)
        assert "include_router" not in content
