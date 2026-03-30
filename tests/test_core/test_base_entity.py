"""Tests for faststack_core.base.entity — the abstract entity hierarchy.

Uses aiosqlite for async in-memory SQLAlchemy testing. A concrete model
(Item) inherits from FullAuditedEntity so every field in the hierarchy is
exercised end-to-end.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Mapped, mapped_column

from faststack_core.base.entity import (
    AuditedEntity,
    Base,
    Entity,
    FullAuditedEntity,
    SoftDeleteEntity,
)

# ---------------------------------------------------------------------------
# Concrete test model
# ---------------------------------------------------------------------------


class Item(FullAuditedEntity):
    """Concrete model used exclusively for testing."""

    __tablename__ = "items"

    name: Mapped[str] = mapped_column(String(100))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(async_engine):
    async_session = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


# ---------------------------------------------------------------------------
# Entity — UUID primary key
# ---------------------------------------------------------------------------


async def test_entity_has_uuid_pk():
    """Entity declares a UUID primary key column."""
    # Entity is abstract, so inspect via the concrete Item table
    pk_cols = [c for c in Item.__table__.columns if c.primary_key]
    assert len(pk_cols) == 1
    assert pk_cols[0].name == "id"


async def test_uuid_auto_generated_on_create(session: AsyncSession):
    """UUID primary key is automatically populated when no id is provided."""
    item = Item(name="auto-uuid")
    session.add(item)
    await session.flush()

    assert item.id is not None
    assert isinstance(item.id, uuid.UUID)


# ---------------------------------------------------------------------------
# AuditedEntity fields
# ---------------------------------------------------------------------------


async def test_audited_entity_fields_exist():
    """AuditedEntity contributes created_at, updated_at, created_by, updated_by."""
    col_names = {c.name for c in Item.__table__.columns}
    for field in ("created_at", "updated_at", "created_by", "updated_by"):
        assert field in col_names, f"Missing audited field: {field}"


async def test_created_at_auto_set(session: AsyncSession):
    """created_at is automatically set on insert."""
    before = datetime.now(UTC)
    item = Item(name="audit-test")
    session.add(item)
    await session.flush()
    after = datetime.now(UTC)

    assert item.created_at is not None
    assert before <= item.created_at <= after


async def test_updated_at_auto_set(session: AsyncSession):
    """updated_at is automatically set on insert."""
    item = Item(name="update-test")
    session.add(item)
    await session.flush()

    assert item.updated_at is not None
    assert isinstance(item.updated_at, datetime)


async def test_created_by_defaults_to_none(session: AsyncSession):
    """created_by defaults to None when not explicitly provided."""
    item = Item(name="no-author")
    session.add(item)
    await session.flush()

    assert item.created_by is None


async def test_updated_by_defaults_to_none(session: AsyncSession):
    """updated_by defaults to None when not explicitly provided."""
    item = Item(name="no-updater")
    session.add(item)
    await session.flush()

    assert item.updated_by is None


# ---------------------------------------------------------------------------
# SoftDeleteEntity fields
# ---------------------------------------------------------------------------


async def test_soft_delete_entity_fields_exist():
    """SoftDeleteEntity contributes is_deleted, deleted_at, deleted_by."""
    col_names = {c.name for c in Item.__table__.columns}
    for field in ("is_deleted", "deleted_at", "deleted_by"):
        assert field in col_names, f"Missing soft-delete field: {field}"


async def test_is_deleted_defaults_false(session: AsyncSession):
    """is_deleted defaults to False on new records."""
    item = Item(name="alive")
    session.add(item)
    await session.flush()

    assert item.is_deleted is False


async def test_deleted_at_defaults_to_none(session: AsyncSession):
    """deleted_at defaults to None on new records."""
    item = Item(name="not-deleted")
    session.add(item)
    await session.flush()

    assert item.deleted_at is None


async def test_deleted_by_defaults_to_none(session: AsyncSession):
    """deleted_by defaults to None on new records."""
    item = Item(name="no-deleter")
    session.add(item)
    await session.flush()

    assert item.deleted_by is None


# ---------------------------------------------------------------------------
# FullAuditedEntity — MRO / diamond inheritance
# ---------------------------------------------------------------------------


async def test_full_audited_entity_has_all_fields():
    """FullAuditedEntity combines every field from both parents."""
    col_names = {c.name for c in Item.__table__.columns}
    expected = {
        "id",
        "name",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "is_deleted",
        "deleted_at",
        "deleted_by",
    }
    assert expected.issubset(col_names), f"Missing columns: {expected - col_names}"


async def test_full_audited_entity_mro():
    """FullAuditedEntity's MRO includes both AuditedEntity and SoftDeleteEntity."""
    mro = FullAuditedEntity.__mro__
    assert AuditedEntity in mro
    assert SoftDeleteEntity in mro
    assert Entity in mro


# ---------------------------------------------------------------------------
# Persistence round-trip
# ---------------------------------------------------------------------------


async def test_persist_and_retrieve(session: AsyncSession):
    """A concrete FullAuditedEntity model can be persisted and retrieved."""
    item = Item(name="round-trip", created_by="tester", updated_by="tester")
    session.add(item)
    await session.flush()

    item_id = item.id

    # Expire and re-fetch from the DB to prove persistence
    await session.commit()
    loaded = await session.get(Item, item_id)

    assert loaded is not None
    assert loaded.name == "round-trip"
    assert loaded.created_by == "tester"
    assert loaded.is_deleted is False
    assert isinstance(loaded.id, uuid.UUID)
    assert loaded.id == item_id
