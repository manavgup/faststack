"""Tests for cli.yaml_parser — YAML entity definition parsing."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from cli.yaml_parser import (
    EntityDefinition,
    FieldDefinition,
    RelationshipDefinition,
    parse_entities_yaml,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_YAML = dedent("""\
    entities:
      User:
        base: FullAuditedEntity
        fields:
          email: {type: string, unique: true, required: true}
          name: {type: string, required: true}
          role: {type: enum, values: [admin, editor, viewer], default: '"viewer"'}
          bio: {type: text}
        searchable: [email, name]
      Post:
        base: AuditedEntity
        fields:
          title: {type: string, required: true}
          content: {type: text}
          status: {type: enum, values: [draft, published, archived], default: '"draft"'}
          tags: {type: array, items: string}
          metadata: {type: jsonb}
          user_id: {type: uuid, references: User}
        searchable: [title]
      Category:
        base: AuditedEntity
        fields:
          name: {type: string, required: true}
          parent_id: {type: uuid, references: self}
""")


@pytest.fixture()
def sample_yaml_path(tmp_path: Path) -> Path:
    """Write the sample YAML to a temp file and return the path."""
    p = tmp_path / "entities.yaml"
    p.write_text(SAMPLE_YAML, encoding="utf-8")
    return p


@pytest.fixture()
def parsed_entities(sample_yaml_path: Path) -> list[EntityDefinition]:
    """Parse the sample YAML and return entity definitions."""
    return parse_entities_yaml(sample_yaml_path)


# ---------------------------------------------------------------------------
# Basic structure tests
# ---------------------------------------------------------------------------


class TestEntityCounts:
    def test_parses_three_entities(self, parsed_entities):
        assert len(parsed_entities) == 3

    def test_entity_names(self, parsed_entities):
        names = [e.name for e in parsed_entities]
        assert names == ["User", "Post", "Category"]


class TestFieldCounts:
    def test_user_has_4_fields(self, parsed_entities):
        user = parsed_entities[0]
        assert user.name == "User"
        assert len(user.fields) == 4

    def test_post_has_6_fields(self, parsed_entities):
        post = parsed_entities[1]
        assert post.name == "Post"
        assert len(post.fields) == 6

    def test_category_has_2_fields(self, parsed_entities):
        category = parsed_entities[2]
        assert category.name == "Category"
        assert len(category.fields) == 2


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------


class TestBaseClass:
    def test_user_base(self, parsed_entities):
        assert parsed_entities[0].base == "FullAuditedEntity"

    def test_post_base(self, parsed_entities):
        assert parsed_entities[1].base == "AuditedEntity"

    def test_category_base(self, parsed_entities):
        assert parsed_entities[2].base == "AuditedEntity"


# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------


class TestRelationships:
    def test_post_has_many_to_one_to_user(self, parsed_entities):
        post = parsed_entities[1]
        assert len(post.relationships) == 1
        rel = post.relationships[0]
        assert rel.type == "many_to_one"
        assert rel.target_entity == "User"
        assert rel.field_name == "user_id"
        assert rel.back_populates == "posts"

    def test_category_has_self_referential(self, parsed_entities):
        category = parsed_entities[2]
        assert len(category.relationships) == 1
        rel = category.relationships[0]
        assert rel.type == "self_referential"
        assert rel.target_entity == "Category"
        assert rel.field_name == "parent_id"
        assert rel.back_populates == "children"

    def test_user_has_no_relationships(self, parsed_entities):
        """User has no FK fields, so no relationships (reverse side is user-added)."""
        user = parsed_entities[0]
        assert len(user.relationships) == 0


# ---------------------------------------------------------------------------
# Enum fields
# ---------------------------------------------------------------------------


class TestEnumFields:
    def test_user_role_enum_values(self, parsed_entities):
        user = parsed_entities[0]
        role_field = next(f for f in user.fields if f.name == "role")
        assert role_field.type == "enum"
        assert role_field.enum_values == ["admin", "editor", "viewer"]
        assert role_field.default == '"viewer"'

    def test_post_status_enum_values(self, parsed_entities):
        post = parsed_entities[1]
        status_field = next(f for f in post.fields if f.name == "status")
        assert status_field.type == "enum"
        assert status_field.enum_values == ["draft", "published", "archived"]
        assert status_field.default == '"draft"'


# ---------------------------------------------------------------------------
# Array fields
# ---------------------------------------------------------------------------


class TestArrayFields:
    def test_post_tags_has_items(self, parsed_entities):
        post = parsed_entities[1]
        tags_field = next(f for f in post.fields if f.name == "tags")
        assert tags_field.type == "array"
        assert tags_field.items == "string"


# ---------------------------------------------------------------------------
# Searchable fields
# ---------------------------------------------------------------------------


class TestSearchableFields:
    def test_user_searchable(self, parsed_entities):
        user = parsed_entities[0]
        assert user.searchable == ["email", "name"]

    def test_post_searchable(self, parsed_entities):
        post = parsed_entities[1]
        assert post.searchable == ["title"]

    def test_category_no_searchable(self, parsed_entities):
        category = parsed_entities[2]
        assert category.searchable == []


# ---------------------------------------------------------------------------
# Table name pluralization
# ---------------------------------------------------------------------------


class TestTableNames:
    def test_user_table_name(self, parsed_entities):
        assert parsed_entities[0].table_name == "users"

    def test_post_table_name(self, parsed_entities):
        assert parsed_entities[1].table_name == "posts"

    def test_category_table_name(self, parsed_entities):
        assert parsed_entities[2].table_name == "categories"


# ---------------------------------------------------------------------------
# Field properties
# ---------------------------------------------------------------------------


class TestFieldProperties:
    def test_email_required_and_unique(self, parsed_entities):
        user = parsed_entities[0]
        email = next(f for f in user.fields if f.name == "email")
        assert email.required is True
        assert email.unique is True

    def test_bio_optional(self, parsed_entities):
        user = parsed_entities[0]
        bio = next(f for f in user.fields if f.name == "bio")
        assert bio.required is False
        assert bio.unique is False

    def test_user_id_references(self, parsed_entities):
        post = parsed_entities[1]
        user_id = next(f for f in post.fields if f.name == "user_id")
        assert user_id.type == "uuid"
        assert user_id.references == "User"

    def test_parent_id_references_self(self, parsed_entities):
        category = parsed_entities[2]
        parent_id = next(f for f in category.fields if f.name == "parent_id")
        assert parent_id.type == "uuid"
        assert parent_id.references == "self"

    def test_metadata_jsonb(self, parsed_entities):
        post = parsed_entities[1]
        meta = next(f for f in post.fields if f.name == "metadata")
        assert meta.type == "jsonb"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_unknown_reference_raises_value_error(self, tmp_path):
        bad_yaml = dedent("""\
            entities:
              Post:
                fields:
                  author_id: {type: uuid, references: Author}
        """)
        p = tmp_path / "bad.yaml"
        p.write_text(bad_yaml, encoding="utf-8")
        with pytest.raises(ValueError, match="unknown entity 'Author'"):
            parse_entities_yaml(p)

    def test_missing_file_raises_file_not_found(self, tmp_path):
        p = tmp_path / "nonexistent.yaml"
        with pytest.raises(FileNotFoundError):
            parse_entities_yaml(p)

    def test_missing_entities_key_raises_value_error(self, tmp_path):
        bad_yaml = "some_key: value\n"
        p = tmp_path / "bad.yaml"
        p.write_text(bad_yaml, encoding="utf-8")
        with pytest.raises(ValueError, match="entities"):
            parse_entities_yaml(p)


# ---------------------------------------------------------------------------
# Dataclass defaults
# ---------------------------------------------------------------------------


class TestDataclassDefaults:
    def test_field_definition_defaults(self):
        fd = FieldDefinition(name="test", type="string")
        assert fd.required is False
        assert fd.unique is False
        assert fd.default is None
        assert fd.references is None
        assert fd.on_delete == "SET NULL"
        assert fd.enum_values == []
        assert fd.items is None

    def test_relationship_definition_defaults(self):
        rd = RelationshipDefinition(
            field_name="user_id",
            type="many_to_one",
            target_entity="User",
        )
        assert rd.back_populates is None

    def test_entity_definition_defaults(self):
        ed = EntityDefinition(name="Test")
        assert ed.base == "FullAuditedEntity"
        assert ed.fields == []
        assert ed.relationships == []
        assert ed.searchable == []
        assert ed.table_name == ""
