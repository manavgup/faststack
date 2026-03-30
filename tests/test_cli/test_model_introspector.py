"""Tests for cli.model_introspector — AST-based SQLAlchemy model reader.

Each test writes a model string to a temp file, introspects it, and verifies
the resulting EntityDefinition matches expectations.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cli.model_introspector import introspect_model

# ── Fixtures: model source strings ───────────────────────────────────

MODEL_SIMPLE = """\
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from faststack_core.base.entity import FullAuditedEntity

class User(FullAuditedEntity):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    bio: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
"""

MODEL_WITH_FK = """\
import uuid
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from faststack_core.base.entity import AuditedEntity

class Post(AuditedEntity):
    __tablename__ = "posts"
    title: Mapped[str] = mapped_column(String(255))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    user: Mapped["User"] = relationship(back_populates="posts")
"""

MODEL_WITH_ENUM = """\
import enum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from faststack_core.base.entity import Entity

class PostStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class Post(Entity):
    __tablename__ = "posts"
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[PostStatus] = mapped_column(default=PostStatus.DRAFT)
"""

MODEL_SELF_REF = """\
import uuid
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from faststack_core.base.entity import Entity

class Category(Entity):
    __tablename__ = "categories"
    name: Mapped[str] = mapped_column(String(255))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("categories.id"))
    parent: Mapped["Category"] = relationship(back_populates="children")
"""

MODEL_ONE_TO_MANY = """\
import uuid
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from faststack_core.base.entity import FullAuditedEntity

class User(FullAuditedEntity):
    __tablename__ = "users"
    name: Mapped[str] = mapped_column(String(255))
    posts: Mapped[list["Post"]] = relationship(back_populates="user")
"""

MODEL_MULTIPLE_TYPES = """\
import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, Integer, Float, DateTime, Date, Numeric, JSON
from sqlalchemy.orm import Mapped, mapped_column
from faststack_core.base.entity import Entity

class Product(Entity):
    __tablename__ = "products"
    name: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[int] = mapped_column(Integer)
    price: Mapped[float] = mapped_column(Float)
    cost: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime)
    launch_date: Mapped[date] = mapped_column(Date)
    metadata_: Mapped[dict] = mapped_column(JSON)
"""


# ── Helper ───────────────────────────────────────────────────────────


def _write_model(tmp_path: Path, source: str, filename: str = "model.py") -> Path:
    """Write *source* to a temp file and return its path."""
    p = tmp_path / filename
    p.write_text(source)
    return p


# ── Tests: simple model ─────────────────────────────────────────────


class TestSimpleModel:
    """Introspect a model with basic fields (string, text, boolean)."""

    def test_class_name(self, tmp_path: Path) -> None:
        entity = introspect_model(_write_model(tmp_path, MODEL_SIMPLE))
        assert entity.name == "User"

    def test_base_class(self, tmp_path: Path) -> None:
        entity = introspect_model(_write_model(tmp_path, MODEL_SIMPLE))
        assert entity.base == "FullAuditedEntity"

    def test_table_name(self, tmp_path: Path) -> None:
        entity = introspect_model(_write_model(tmp_path, MODEL_SIMPLE))
        assert entity.table_name == "users"

    def test_field_count(self, tmp_path: Path) -> None:
        entity = introspect_model(_write_model(tmp_path, MODEL_SIMPLE))
        assert len(entity.fields) == 4

    def test_email_unique(self, tmp_path: Path) -> None:
        entity = introspect_model(_write_model(tmp_path, MODEL_SIMPLE))
        email = next(f for f in entity.fields if f.name == "email")
        assert email.unique is True
        assert email.type == "string"
        assert email.required is True

    def test_name_field(self, tmp_path: Path) -> None:
        entity = introspect_model(_write_model(tmp_path, MODEL_SIMPLE))
        name = next(f for f in entity.fields if f.name == "name")
        assert name.type == "string"
        assert name.required is True
        assert name.unique is False

    def test_bio_nullable(self, tmp_path: Path) -> None:
        entity = introspect_model(_write_model(tmp_path, MODEL_SIMPLE))
        bio = next(f for f in entity.fields if f.name == "bio")
        assert bio.required is False

    def test_is_active_default(self, tmp_path: Path) -> None:
        entity = introspect_model(_write_model(tmp_path, MODEL_SIMPLE))
        active = next(f for f in entity.fields if f.name == "is_active")
        assert active.type == "boolean"
        assert active.default == "True"

    def test_no_relationships(self, tmp_path: Path) -> None:
        entity = introspect_model(_write_model(tmp_path, MODEL_SIMPLE))
        assert entity.relationships == []


# ── Tests: FK and relationship ───────────────────────────────────────


class TestForeignKeyModel:
    """Introspect a model with a FK and explicit relationship()."""

    def test_class_name(self, tmp_path: Path) -> None:
        entity = introspect_model(_write_model(tmp_path, MODEL_WITH_FK))
        assert entity.name == "Post"

    def test_base_class(self, tmp_path: Path) -> None:
        entity = introspect_model(_write_model(tmp_path, MODEL_WITH_FK))
        assert entity.base == "AuditedEntity"

    def test_user_id_field_type(self, tmp_path: Path) -> None:
        entity = introspect_model(_write_model(tmp_path, MODEL_WITH_FK))
        uid = next(f for f in entity.fields if f.name == "user_id")
        assert uid.type == "uuid"

    def test_user_id_references(self, tmp_path: Path) -> None:
        entity = introspect_model(_write_model(tmp_path, MODEL_WITH_FK))
        uid = next(f for f in entity.fields if f.name == "user_id")
        assert uid.references == "User"

    def test_has_relationship(self, tmp_path: Path) -> None:
        entity = introspect_model(_write_model(tmp_path, MODEL_WITH_FK))
        assert len(entity.relationships) >= 1

    def test_relationship_type(self, tmp_path: Path) -> None:
        entity = introspect_model(_write_model(tmp_path, MODEL_WITH_FK))
        rel = next(r for r in entity.relationships if r.target_entity == "User")
        assert rel.type == "many_to_one"

    def test_relationship_back_populates(self, tmp_path: Path) -> None:
        entity = introspect_model(_write_model(tmp_path, MODEL_WITH_FK))
        rel = next(r for r in entity.relationships if r.target_entity == "User")
        assert rel.back_populates == "posts"

    def test_not_self_referential(self, tmp_path: Path) -> None:
        entity = introspect_model(_write_model(tmp_path, MODEL_WITH_FK))
        rel = next(r for r in entity.relationships if r.target_entity == "User")
        assert rel.type == "many_to_one"  # not self_referential


# ── Tests: enum ──────────────────────────────────────────────────────


class TestEnumModel:
    """Introspect a model that uses a ``str, enum.Enum`` class."""

    def test_skips_enum_class(self, tmp_path: Path) -> None:
        entity = introspect_model(_write_model(tmp_path, MODEL_WITH_ENUM))
        assert entity.name == "Post"  # not PostStatus

    def test_status_field_type(self, tmp_path: Path) -> None:
        entity = introspect_model(_write_model(tmp_path, MODEL_WITH_ENUM))
        status = next(f for f in entity.fields if f.name == "status")
        assert status.type == "enum"

    def test_enum_values(self, tmp_path: Path) -> None:
        entity = introspect_model(_write_model(tmp_path, MODEL_WITH_ENUM))
        status = next(f for f in entity.fields if f.name == "status")
        assert status.enum_values == ["draft", "published", "archived"]

    def test_enum_default(self, tmp_path: Path) -> None:
        entity = introspect_model(_write_model(tmp_path, MODEL_WITH_ENUM))
        status = next(f for f in entity.fields if f.name == "status")
        assert status.default == "PostStatus.DRAFT"

    def test_field_count(self, tmp_path: Path) -> None:
        entity = introspect_model(_write_model(tmp_path, MODEL_WITH_ENUM))
        assert len(entity.fields) == 2  # title + status


# ── Tests: self-referential ──────────────────────────────────────────


class TestSelfReferentialModel:
    """Introspect a model with a self-referential FK."""

    def test_class_name(self, tmp_path: Path) -> None:
        entity = introspect_model(_write_model(tmp_path, MODEL_SELF_REF))
        assert entity.name == "Category"

    def test_parent_id_nullable(self, tmp_path: Path) -> None:
        entity = introspect_model(_write_model(tmp_path, MODEL_SELF_REF))
        pid = next(f for f in entity.fields if f.name == "parent_id")
        assert pid.required is False

    def test_self_referential_relationship(self, tmp_path: Path) -> None:
        entity = introspect_model(_write_model(tmp_path, MODEL_SELF_REF))
        rel = next(r for r in entity.relationships if r.target_entity == "Category")
        assert rel.type == "self_referential"

    def test_relationship_back_populates(self, tmp_path: Path) -> None:
        entity = introspect_model(_write_model(tmp_path, MODEL_SELF_REF))
        rel = next(r for r in entity.relationships if r.field_name == "parent")
        assert rel.back_populates == "children"

    def test_parent_id_references_self(self, tmp_path: Path) -> None:
        entity = introspect_model(_write_model(tmp_path, MODEL_SELF_REF))
        pid = next(f for f in entity.fields if f.name == "parent_id")
        assert pid.references == "Category"


# ── Tests: one-to-many ───────────────────────────────────────────────


class TestOneToManyModel:
    """Introspect a model with a ``list["Post"]`` relationship."""

    def test_relationship_type(self, tmp_path: Path) -> None:
        entity = introspect_model(_write_model(tmp_path, MODEL_ONE_TO_MANY))
        rel = next(r for r in entity.relationships if r.target_entity == "Post")
        assert rel.type == "one_to_many"

    def test_relationship_back_populates(self, tmp_path: Path) -> None:
        entity = introspect_model(_write_model(tmp_path, MODEL_ONE_TO_MANY))
        rel = next(r for r in entity.relationships if r.target_entity == "Post")
        assert rel.back_populates == "user"


# ── Tests: multiple types ────────────────────────────────────────────


class TestMultipleTypes:
    """Verify that all supported annotation types map correctly."""

    @pytest.fixture()
    def entity(self, tmp_path: Path):
        return introspect_model(_write_model(tmp_path, MODEL_MULTIPLE_TYPES))

    def test_string_type(self, entity) -> None:
        f = next(f for f in entity.fields if f.name == "name")
        assert f.type == "string"

    def test_integer_type(self, entity) -> None:
        f = next(f for f in entity.fields if f.name == "quantity")
        assert f.type == "integer"

    def test_float_type(self, entity) -> None:
        f = next(f for f in entity.fields if f.name == "price")
        assert f.type == "float"

    def test_decimal_type(self, entity) -> None:
        f = next(f for f in entity.fields if f.name == "cost")
        assert f.type == "decimal"

    def test_datetime_type(self, entity) -> None:
        f = next(f for f in entity.fields if f.name == "created_at")
        assert f.type == "datetime"

    def test_date_type(self, entity) -> None:
        f = next(f for f in entity.fields if f.name == "launch_date")
        assert f.type == "date"

    def test_json_type(self, entity) -> None:
        f = next(f for f in entity.fields if f.name == "metadata_")
        assert f.type == "json"

    def test_table_name(self, entity) -> None:
        assert entity.table_name == "products"

    def test_field_count(self, entity) -> None:
        assert len(entity.fields) == 7


# ── Tests: error cases ───────────────────────────────────────────────


class TestErrorCases:
    """Edge cases and error handling."""

    def test_no_model_raises(self, tmp_path: Path) -> None:
        source = "x = 1\n"
        with pytest.raises(ValueError, match="No model class found"):
            introspect_model(_write_model(tmp_path, source))

    def test_enum_only_raises(self, tmp_path: Path) -> None:
        source = """\
import enum

class Status(str, enum.Enum):
    A = "a"
"""
        with pytest.raises(ValueError, match="No model class found"):
            introspect_model(_write_model(tmp_path, source))
