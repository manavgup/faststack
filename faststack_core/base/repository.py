"""Repository Protocol and async SQLAlchemy implementation.

Defines the contract (``Repository`` Protocol) that all repository
implementations — including in-memory fakes — must satisfy via structural
typing.  Also provides ``SqlAlchemyRepository``, the production
implementation backed by an ``AsyncSession``.

See ADR-002 for the design rationale: Protocol over ABC, fakes over mocks.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Generic, Protocol, TypeVar, runtime_checkable
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from faststack_core.base.entity import Entity, SoftDeleteEntity
from faststack_core.exceptions.domain import NotFoundError

T = TypeVar("T", bound=Entity)


# ---------------------------------------------------------------------------
# Protocol — the contract
# ---------------------------------------------------------------------------


@runtime_checkable
class Repository(Protocol[T]):
    """Base repository contract.  All methods are async.

    Any class that implements these method signatures satisfies the
    Protocol via structural typing — no inheritance required.
    """

    async def get_by_id(self, id: UUID) -> T | None: ...

    async def list(self, skip: int = 0, limit: int = 100) -> list[T]: ...

    async def create(self, data: dict) -> T: ...

    async def update(self, id: UUID, data: dict) -> T: ...

    async def delete(self, id: UUID) -> None: ...

    async def count(self) -> int: ...


@runtime_checkable
class SearchableRepository(Repository[T], Protocol):
    """Extended contract with full-text search and sorting."""

    async def search(
        self, query: str, fields: list[str], skip: int = 0, limit: int = 100
    ) -> list[T]: ...


# ---------------------------------------------------------------------------
# SQLAlchemy implementation
# ---------------------------------------------------------------------------


class SqlAlchemyRepository(Generic[T]):
    """Async SQLAlchemy implementation satisfying the ``Repository`` Protocol.

    Parameters
    ----------
    db:
        An active ``AsyncSession``.
    model:
        The SQLAlchemy model class (a concrete subclass of ``Entity``).
    """

    def __init__(self, db: AsyncSession, model: type[T]) -> None:
        self.db = db
        self.model = model

    async def get_by_id(self, id: UUID) -> T | None:
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)  # type: ignore[attr-defined]
        )
        return result.scalar_one_or_none()

    async def list(self, skip: int = 0, limit: int = 100) -> list[T]:
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, data: dict) -> T:
        entity = self.model(**data)
        self.db.add(entity)
        await self.db.flush()
        await self.db.refresh(entity)
        return entity

    async def update(self, id: UUID, data: dict) -> T:
        entity = await self.get_by_id(id)
        if not entity:
            raise NotFoundError(f"{self.model.__name__} with id {id} not found")
        for key, value in data.items():
            setattr(entity, key, value)
        await self.db.flush()
        await self.db.refresh(entity)
        return entity

    async def delete(self, id: UUID) -> None:
        entity = await self.get_by_id(id)
        if not entity:
            raise NotFoundError(f"{self.model.__name__} with id {id} not found")
        if isinstance(entity, SoftDeleteEntity):
            entity.is_deleted = True  # type: ignore[attr-defined]
            entity.deleted_at = datetime.now(UTC)  # type: ignore[attr-defined]
            await self.db.flush()
        else:
            await self.db.delete(entity)
            await self.db.flush()

    async def hard_delete(self, id: UUID) -> None:
        """Permanently remove the entity, ignoring soft-delete."""
        entity = await self.get_by_id(id)
        if not entity:
            raise NotFoundError(f"{self.model.__name__} with id {id} not found")
        await self.db.delete(entity)
        await self.db.flush()

    async def count(self) -> int:
        result = await self.db.execute(select(func.count()).select_from(self.model))
        return result.scalar_one()
