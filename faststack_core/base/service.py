"""CRUD service with async lifecycle hooks.

Provides ``CrudService`` — a generic service that wraps a ``Repository``
and exposes create/get/list/update/delete operations with before/after
hooks at each step.  Users override only the hooks they need in their
generated service files.

See ADR-005 for the design rationale: hooks over method overrides.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar
from uuid import UUID

from faststack_core.base.entity import Entity
from faststack_core.base.repository import Repository
from faststack_core.exceptions.domain import NotFoundError

T = TypeVar("T", bound=Entity)


class CrudService(Generic[T]):
    """Generic async CRUD service with lifecycle hooks.

    Parameters
    ----------
    repository:
        Any object satisfying the ``Repository[T]`` Protocol.

    Hooks
    -----
    Override these ``async`` methods in your generated service to inject
    custom logic.  Each hook has a default no-op implementation.

    - ``before_create(data)``  → transform / validate before persisting
    - ``after_create(entity)`` → side-effects after creation
    - ``before_update(id, data)`` → transform / validate before update
    - ``after_update(entity)``  → side-effects after update
    - ``before_delete(id)``  → guard / validate before deletion
    - ``after_delete(id)``   → cleanup after deletion
    """

    def __init__(self, repository: Repository[T]) -> None:
        self.repository = repository

    # ------------------------------------------------------------------
    # Lifecycle hooks — override in subclasses
    # ------------------------------------------------------------------

    async def before_create(self, data: dict[str, Any]) -> dict[str, Any]:
        return data

    async def after_create(self, entity: T) -> T:
        return entity

    async def before_update(self, id: UUID, data: dict[str, Any]) -> dict[str, Any]:
        return data

    async def after_update(self, entity: T) -> T:
        return entity

    async def before_delete(self, id: UUID) -> None:
        pass

    async def after_delete(self, id: UUID) -> None:
        pass

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------

    async def create(self, data: dict[str, Any]) -> T:
        data = await self.before_create(data)
        entity = await self.repository.create(data)
        return await self.after_create(entity)

    async def get(self, id: UUID) -> T:
        entity = await self.repository.get_by_id(id)
        if not entity:
            raise NotFoundError(f"Entity with id {id} not found")
        return entity

    async def list(self, skip: int = 0, limit: int = 100) -> list[T]:
        return await self.repository.list(skip=skip, limit=limit)

    async def update(self, id: UUID, data: dict[str, Any]) -> T:
        data = await self.before_update(id, data)
        entity = await self.repository.update(id, data)
        return await self.after_update(entity)

    async def delete(self, id: UUID) -> None:
        await self.before_delete(id)
        await self.repository.delete(id)
        await self.after_delete(id)
