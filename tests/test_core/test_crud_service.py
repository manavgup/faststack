"""Tests for CrudService with lifecycle hooks.

Uses an in-memory fake repository (not SqlAlchemyRepository) to test
pure business logic without any database. This is the pattern generated
projects will use for unit tests.
"""

import uuid
from typing import Any
from uuid import UUID

import pytest

from faststack_core.base.service import CrudService
from faststack_core.exceptions.domain import NotFoundError

# ---------------------------------------------------------------------------
# Fake entity + repository
# ---------------------------------------------------------------------------


class FakeEntity:
    """Minimal entity stand-in for testing."""

    def __init__(self, **kwargs: Any) -> None:
        self.id: UUID = kwargs.get("id", uuid.uuid4())
        for key, value in kwargs.items():
            setattr(self, key, value)


class FakeRepository:
    """In-memory repository satisfying the Repository Protocol."""

    def __init__(self) -> None:
        self._store: dict[UUID, FakeEntity] = {}

    async def get_by_id(self, id: UUID) -> FakeEntity | None:
        return self._store.get(id)

    async def list(self, skip: int = 0, limit: int = 100) -> list[FakeEntity]:
        items = list(self._store.values())
        return items[skip : skip + limit]

    async def create(self, data: dict) -> FakeEntity:
        entity = FakeEntity(**data)
        self._store[entity.id] = entity
        return entity

    async def update(self, id: UUID, data: dict) -> FakeEntity:
        entity = self._store.get(id)
        if not entity:
            raise NotFoundError(f"Entity {id} not found")
        for key, value in data.items():
            setattr(entity, key, value)
        return entity

    async def delete(self, id: UUID) -> None:
        if id not in self._store:
            raise NotFoundError(f"Entity {id} not found")
        del self._store[id]

    async def count(self) -> int:
        return len(self._store)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def repo():
    return FakeRepository()


@pytest.fixture
def service(repo):
    return CrudService(repo)


# ---------------------------------------------------------------------------
# Basic CRUD
# ---------------------------------------------------------------------------


async def test_create(service):
    entity = await service.create({"name": "test"})
    assert entity.name == "test"
    assert entity.id is not None


async def test_get(service):
    entity = await service.create({"name": "findable"})
    found = await service.get(entity.id)
    assert found.id == entity.id


async def test_get_not_found(service):
    with pytest.raises(NotFoundError):
        await service.get(uuid.uuid4())


async def test_list_empty(service):
    result = await service.list()
    assert result == []


async def test_list_with_items(service):
    await service.create({"name": "a"})
    await service.create({"name": "b"})
    result = await service.list()
    assert len(result) == 2


async def test_update(service):
    entity = await service.create({"name": "before"})
    updated = await service.update(entity.id, {"name": "after"})
    assert updated.name == "after"


async def test_delete(service):
    entity = await service.create({"name": "doomed"})
    await service.delete(entity.id)
    with pytest.raises(NotFoundError):
        await service.get(entity.id)


# ---------------------------------------------------------------------------
# Lifecycle hooks fire in correct order
# ---------------------------------------------------------------------------


async def test_before_create_transforms_data(repo):
    """before_create can modify data before it reaches the repository."""

    class TransformService(CrudService):
        async def before_create(self, data):
            data["name"] = data["name"].upper()
            return data

    svc = TransformService(repo)
    entity = await svc.create({"name": "lowercase"})
    assert entity.name == "LOWERCASE"


async def test_after_create_receives_entity(repo):
    """after_create receives the created entity and can transform it."""
    called_with = {}

    class TrackingService(CrudService):
        async def after_create(self, entity):
            called_with["id"] = entity.id
            called_with["name"] = entity.name
            return entity

    svc = TrackingService(repo)
    entity = await svc.create({"name": "tracked"})
    assert called_with["id"] == entity.id
    assert called_with["name"] == "tracked"


async def test_before_update_transforms_data(repo):
    """before_update can modify data before it reaches the repository."""

    class TransformService(CrudService):
        async def before_update(self, id, data):
            data["name"] = data["name"].strip()
            return data

    svc = TransformService(repo)
    entity = await svc.create({"name": "original"})
    updated = await svc.update(entity.id, {"name": "  padded  "})
    assert updated.name == "padded"


async def test_after_update_receives_entity(repo):
    """after_update receives the updated entity."""
    called_with = {}

    class TrackingService(CrudService):
        async def after_update(self, entity):
            called_with["name"] = entity.name
            return entity

    svc = TrackingService(repo)
    entity = await svc.create({"name": "before"})
    await svc.update(entity.id, {"name": "after"})
    assert called_with["name"] == "after"


async def test_before_delete_can_guard(repo):
    """before_delete can raise to prevent deletion."""

    class GuardedService(CrudService):
        async def before_delete(self, id):
            raise NotFoundError("Deletion blocked by guard")

    svc = GuardedService(repo)
    entity = await svc.create({"name": "protected"})
    with pytest.raises(NotFoundError, match="Deletion blocked"):
        await svc.delete(entity.id)

    # Entity should still exist
    assert await repo.get_by_id(entity.id) is not None


async def test_after_delete_fires(repo):
    """after_delete is called after successful deletion."""
    deleted_ids = []

    class TrackingService(CrudService):
        async def after_delete(self, id):
            deleted_ids.append(id)

    svc = TrackingService(repo)
    entity = await svc.create({"name": "tracked-delete"})
    await svc.delete(entity.id)
    assert entity.id in deleted_ids


async def test_hook_execution_order(repo):
    """Hooks execute in the correct order: before → operation → after."""
    call_log = []

    class OrderedService(CrudService):
        async def before_create(self, data):
            call_log.append("before_create")
            return data

        async def after_create(self, entity):
            call_log.append("after_create")
            return entity

    svc = OrderedService(repo)
    await svc.create({"name": "ordered"})
    assert call_log == ["before_create", "after_create"]
