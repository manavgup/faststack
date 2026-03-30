"""Tests for simple mode entity templates.

Renders all 9 templates for User/Post/Category entities from the design
plan YAML example. Verifies:
- Output is syntactically valid Python (ast.parse)
- Cross-template consistency (names, imports match)
"""

import ast
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

from cli.yaml_parser import EntityDefinition, FieldDefinition, RelationshipDefinition

TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates" / "simple"


# ---------------------------------------------------------------------------
# Test entities (from design plan YAML example)
# ---------------------------------------------------------------------------

USER_ENTITY = EntityDefinition(
    name="User",
    base="FullAuditedEntity",
    table_name="users",
    fields=[
        FieldDefinition(name="email", type="string", required=True, unique=True),
        FieldDefinition(name="name", type="string", required=True),
        FieldDefinition(
            name="role",
            type="enum",
            enum_values=["admin", "editor", "viewer"],
            default='"viewer"',
        ),
        FieldDefinition(name="bio", type="text"),
    ],
    relationships=[],
    searchable=["email", "name"],
)

POST_ENTITY = EntityDefinition(
    name="Post",
    base="AuditedEntity",
    table_name="posts",
    fields=[
        FieldDefinition(name="title", type="string", required=True),
        FieldDefinition(name="content", type="text"),
        FieldDefinition(
            name="status",
            type="enum",
            enum_values=["draft", "published", "archived"],
            default='"draft"',
        ),
        FieldDefinition(name="tags", type="array", items="string"),
        FieldDefinition(name="metadata", type="jsonb"),
        FieldDefinition(name="user_id", type="uuid", references="User"),
    ],
    relationships=[
        RelationshipDefinition(
            field_name="user_id",
            type="many_to_one",
            target_entity="User",
            back_populates="posts",
        ),
    ],
    searchable=["title"],
)

CATEGORY_ENTITY = EntityDefinition(
    name="Category",
    base="AuditedEntity",
    table_name="categories",
    fields=[
        FieldDefinition(name="name", type="string", required=True),
        FieldDefinition(name="parent_id", type="uuid", references="self"),
    ],
    relationships=[
        RelationshipDefinition(
            field_name="parent_id",
            type="self_referential",
            target_entity="Category",
            back_populates="children",
        ),
    ],
    searchable=[],
)

MINIMAL_ENTITY = EntityDefinition(
    name="Tag",
    base="Entity",
    table_name="tags",
    fields=[
        FieldDefinition(name="label", type="string", required=True),
    ],
    relationships=[],
    searchable=[],
)

ALL_ENTITIES = [USER_ENTITY, POST_ENTITY, CATEGORY_ENTITY, MINIMAL_ENTITY]

TEMPLATES = [
    "model.py.j2",
    "schema.py.j2",
    "repository.py.j2",
    "service.py.j2",
    "router.py.j2",
    "factory.py.j2",
    "fake_repository.py.j2",
    "test_unit_service.py.j2",
    "test_integration.py.j2",
]


@pytest.fixture
def jinja_env():
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        keep_trailing_newline=True,
    )


def _render(jinja_env, template_name: str, entity: EntityDefinition) -> str:
    template = jinja_env.get_template(template_name)
    return template.render(entity=entity)


# ---------------------------------------------------------------------------
# Every template renders valid Python for every entity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("template_name", TEMPLATES)
@pytest.mark.parametrize(
    "entity",
    ALL_ENTITIES,
    ids=["User", "Post", "Category", "Tag"],
)
def test_template_renders_valid_python(jinja_env, template_name, entity):
    """Rendered output must be parseable as Python."""
    output = _render(jinja_env, template_name, entity)
    try:
        ast.parse(output)
    except SyntaxError as e:
        pytest.fail(
            f"{template_name} for {entity.name} produced invalid Python:\n"
            f"  {e}\n\nGenerated code:\n{output}"
        )


# ---------------------------------------------------------------------------
# Model template specifics
# ---------------------------------------------------------------------------


def test_model_has_tablename(jinja_env):
    output = _render(jinja_env, "model.py.j2", USER_ENTITY)
    assert '__tablename__ = "users"' in output


def test_model_inherits_base(jinja_env):
    output = _render(jinja_env, "model.py.j2", USER_ENTITY)
    assert "class User(FullAuditedEntity)" in output


def test_model_has_enum_class(jinja_env):
    output = _render(jinja_env, "model.py.j2", USER_ENTITY)
    assert "class UserRole" in output
    assert "ADMIN" in output or "admin" in output.lower()


def test_model_has_fk(jinja_env):
    output = _render(jinja_env, "model.py.j2", POST_ENTITY)
    assert "ForeignKey" in output
    assert "user_id" in output


def test_model_has_relationship(jinja_env):
    output = _render(jinja_env, "model.py.j2", POST_ENTITY)
    assert "relationship" in output


def test_model_self_referential(jinja_env):
    output = _render(jinja_env, "model.py.j2", CATEGORY_ENTITY)
    assert "parent_id" in output
    assert "ForeignKey" in output


# ---------------------------------------------------------------------------
# Schema template specifics
# ---------------------------------------------------------------------------


def test_schema_has_four_classes(jinja_env):
    output = _render(jinja_env, "schema.py.j2", USER_ENTITY)
    assert "class UserCreate" in output
    assert "class UserUpdate" in output
    assert "class UserResponse" in output
    assert "class UserDetailResponse" in output


def test_schema_create_has_required_fields(jinja_env):
    output = _render(jinja_env, "schema.py.j2", USER_ENTITY)
    assert "email:" in output
    assert "name:" in output


def test_schema_response_has_id(jinja_env):
    output = _render(jinja_env, "schema.py.j2", USER_ENTITY)
    assert "id:" in output


# ---------------------------------------------------------------------------
# Repository template specifics
# ---------------------------------------------------------------------------


def test_repository_inherits_sqlalchemy_repo(jinja_env):
    output = _render(jinja_env, "repository.py.j2", USER_ENTITY)
    assert "SqlAlchemyRepository" in output
    assert "class UserRepository" in output


def test_repository_has_search_for_searchable(jinja_env):
    output = _render(jinja_env, "repository.py.j2", USER_ENTITY)
    assert "search" in output


def test_repository_no_search_for_non_searchable(jinja_env):
    output = _render(jinja_env, "repository.py.j2", MINIMAL_ENTITY)
    assert "search" not in output


# ---------------------------------------------------------------------------
# Service template specifics
# ---------------------------------------------------------------------------


def test_service_inherits_crud_service(jinja_env):
    output = _render(jinja_env, "service.py.j2", USER_ENTITY)
    assert "CrudService" in output
    assert "class UserService" in output


def test_service_accepts_repository_protocol(jinja_env):
    output = _render(jinja_env, "service.py.j2", USER_ENTITY)
    assert "Repository" in output


# ---------------------------------------------------------------------------
# Router template specifics
# ---------------------------------------------------------------------------


def test_router_has_crud_endpoints(jinja_env):
    output = _render(jinja_env, "router.py.j2", USER_ENTITY)
    assert "@router.get" in output
    assert "@router.post" in output
    assert "@router.put" in output
    assert "@router.delete" in output


def test_router_has_correct_prefix(jinja_env):
    output = _render(jinja_env, "router.py.j2", USER_ENTITY)
    assert "/users" in output


# ---------------------------------------------------------------------------
# Fake repository template specifics
# ---------------------------------------------------------------------------


def test_fake_has_all_protocol_methods(jinja_env):
    output = _render(jinja_env, "fake_repository.py.j2", USER_ENTITY)
    for method in ("get_by_id", "list", "create", "update", "delete", "count"):
        assert f"async def {method}" in output


def test_fake_uses_dict_store(jinja_env):
    output = _render(jinja_env, "fake_repository.py.j2", USER_ENTITY)
    assert "_store" in output


# ---------------------------------------------------------------------------
# Test templates specifics
# ---------------------------------------------------------------------------


def test_unit_test_has_fixtures(jinja_env):
    output = _render(jinja_env, "test_unit_service.py.j2", USER_ENTITY)
    assert "def repo" in output
    assert "def service" in output
    assert "test_create" in output
    assert "test_get_not_found" in output


def test_integration_test_has_endpoints(jinja_env):
    output = _render(jinja_env, "test_integration.py.j2", USER_ENTITY)
    assert "test_create" in output
    assert "test_list" in output
