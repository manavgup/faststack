"""Base entity classes for SQLAlchemy 2.0 declarative models.

Provides an abstract entity hierarchy with UUID primary keys, audit fields,
and soft-delete support. All classes are abstract — concrete models inherit
from the appropriate level.

Hierarchy:
    Base (DeclarativeBase)
    └── Entity — UUID primary key
        ├── AuditedEntity — created_at/by, updated_at/by
        ├── SoftDeleteEntity — is_deleted, deleted_at/by
        └── FullAuditedEntity(AuditedEntity, SoftDeleteEntity) — all fields
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 declarative base for all FastStack models."""

    pass


class Entity(Base):
    """Abstract entity with a UUID primary key.

    Every persistent domain object inherits from this class (directly or
    through one of the audited variants).
    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class AuditedEntity(Entity):
    """Abstract entity that tracks creation and last-update metadata.

    Fields:
        created_at: UTC timestamp set automatically on insert.
        updated_at: UTC timestamp set automatically on insert and update.
        created_by: Optional identifier of the user who created the record.
        updated_by: Optional identifier of the user who last updated the record.
    """

    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
    created_by: Mapped[str | None] = mapped_column(String(255), default=None)
    updated_by: Mapped[str | None] = mapped_column(String(255), default=None)


class SoftDeleteEntity(Entity):
    """Abstract entity that supports soft deletion.

    Instead of removing rows, soft-deleted records are flagged so they can
    be excluded from normal queries while remaining recoverable.

    Fields:
        is_deleted: Whether the record has been soft-deleted.
        deleted_at: UTC timestamp of when the record was soft-deleted.
        deleted_by: Optional identifier of the user who deleted the record.
    """

    __abstract__ = True

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    deleted_by: Mapped[str | None] = mapped_column(String(255), default=None)


class FullAuditedEntity(AuditedEntity, SoftDeleteEntity):
    """Abstract entity combining audit tracking and soft-delete support.

    Diamond inheritance is resolved cleanly because every intermediate class
    sets ``__abstract__ = True``, so SQLAlchemy never tries to map more than
    one table for the shared ``Entity`` ancestor.

    Includes all fields from both :class:`AuditedEntity` and
    :class:`SoftDeleteEntity`.
    """

    __abstract__ = True
