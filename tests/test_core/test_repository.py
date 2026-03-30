"""Tests for Repository Protocol conformance and SqlAlchemyRepository.

Uses aiosqlite for async in-memory SQLAlchemy testing.
"""

import uuid

import pytest
from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Mapped, mapped_column

from faststack_core.base.entity import Base, Entity, FullAuditedEntity
from faststack_core.base.repository import Repository, SqlAlchemyRepository
from faststack_core.exceptions.domain import NotFoundError

# ---------------------------------------------------------------------------
# Test models
# ---------------------------------------------------------------------------


class SimpleItem(Entity):
    """Non-soft-delete entity for testing hard delete behavior."""

    __tablename__ = "simple_items"
    name: Mapped[str] = mapped_column(String(100))


class AuditedItem(FullAuditedEntity):
    """Soft-delete entity for testing soft delete behavior."""

    __tablename__ = "audited_items"
    name: Mapped[str] = mapped_column(String(100))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def session(engine):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess


@pytest.fixture
def simple_repo(session):
    return SqlAlchemyRepository(session, SimpleItem)


@pytest.fixture
def audited_repo(session):
    return SqlAlchemyRepository(session, AuditedItem)


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


class FakeRepo:
    """Minimal fake that satisfies Repository Protocol via structural typing."""

    async def get_by_id(self, id: uuid.UUID) -> None:
        return None

    async def list(self, skip: int = 0, limit: int = 100) -> list:
        return []

    async def create(self, data: dict) -> None:
        return None

    async def update(self, id: uuid.UUID, data: dict) -> None:
        return None

    async def delete(self, id: uuid.UUID) -> None:
        pass

    async def count(self) -> int:
        return 0


async def test_sqlalchemy_repo_satisfies_protocol():
    """SqlAlchemyRepository is recognized as a Repository at runtime."""
    assert isinstance(SqlAlchemyRepository, type)
    # We can't isinstance-check a generic, but we can verify method signatures exist
    for method in ("get_by_id", "list", "create", "update", "delete", "count"):
        assert hasattr(SqlAlchemyRepository, method)


async def test_fake_repo_satisfies_protocol():
    """A plain class with matching methods satisfies the Protocol."""
    fake = FakeRepo()
    assert isinstance(fake, Repository)


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------


async def test_create(simple_repo):
    item = await simple_repo.create({"name": "test-item"})
    assert item.name == "test-item"
    assert item.id is not None
    assert isinstance(item.id, uuid.UUID)


async def test_get_by_id(simple_repo):
    item = await simple_repo.create({"name": "findable"})
    found = await simple_repo.get_by_id(item.id)
    assert found is not None
    assert found.id == item.id
    assert found.name == "findable"


async def test_get_by_id_not_found(simple_repo):
    result = await simple_repo.get_by_id(uuid.uuid4())
    assert result is None


async def test_list_empty(simple_repo):
    items = await simple_repo.list()
    assert items == []


async def test_list_with_items(simple_repo):
    await simple_repo.create({"name": "a"})
    await simple_repo.create({"name": "b"})
    await simple_repo.create({"name": "c"})
    items = await simple_repo.list()
    assert len(items) == 3


async def test_list_with_skip_and_limit(simple_repo):
    for i in range(5):
        await simple_repo.create({"name": f"item-{i}"})
    items = await simple_repo.list(skip=1, limit=2)
    assert len(items) == 2


async def test_update(simple_repo):
    item = await simple_repo.create({"name": "before"})
    updated = await simple_repo.update(item.id, {"name": "after"})
    assert updated.name == "after"
    assert updated.id == item.id


async def test_update_not_found(simple_repo):
    with pytest.raises(NotFoundError):
        await simple_repo.update(uuid.uuid4(), {"name": "nope"})


async def test_count_empty(simple_repo):
    assert await simple_repo.count() == 0


async def test_count_with_items(simple_repo):
    await simple_repo.create({"name": "one"})
    await simple_repo.create({"name": "two"})
    assert await simple_repo.count() == 2


# ---------------------------------------------------------------------------
# Hard delete (non-soft-delete entity)
# ---------------------------------------------------------------------------


async def test_delete_hard_deletes_simple_entity(simple_repo):
    item = await simple_repo.create({"name": "to-delete"})
    await simple_repo.delete(item.id)
    assert await simple_repo.get_by_id(item.id) is None


async def test_delete_not_found(simple_repo):
    with pytest.raises(NotFoundError):
        await simple_repo.delete(uuid.uuid4())


# ---------------------------------------------------------------------------
# Soft delete (FullAuditedEntity)
# ---------------------------------------------------------------------------


async def test_delete_soft_deletes_audited_entity(audited_repo):
    item = await audited_repo.create({"name": "soft-target"})
    await audited_repo.delete(item.id)

    # Entity still exists in DB but is flagged
    found = await audited_repo.get_by_id(item.id)
    assert found is not None
    assert found.is_deleted is True
    assert found.deleted_at is not None


async def test_hard_delete_removes_audited_entity(audited_repo):
    item = await audited_repo.create({"name": "hard-target"})
    await audited_repo.hard_delete(item.id)
    assert await audited_repo.get_by_id(item.id) is None


async def test_hard_delete_not_found(audited_repo):
    with pytest.raises(NotFoundError):
        await audited_repo.hard_delete(uuid.uuid4())
