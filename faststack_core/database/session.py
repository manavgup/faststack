"""Async database session configuration for FastStack.

Provides helpers to create an async SQLAlchemy engine and session factory,
plus a FastAPI-compatible dependency that yields a transactional session.
"""

from collections.abc import AsyncGenerator
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


@dataclass
class DatabaseConfig:
    """Connection parameters for an async SQLAlchemy engine.

    ``pool_size``, ``max_overflow``, and ``pool_timeout`` are silently
    ignored for SQLite URLs because aiosqlite uses a
    :class:`~sqlalchemy.pool.StaticPool` that does not support them.
    """

    url: str
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30


def _is_sqlite(url: str) -> bool:
    """Return True when *url* targets an SQLite backend."""
    return url.startswith("sqlite")


def create_engine(config: DatabaseConfig) -> AsyncEngine:
    """Create an async SQLAlchemy engine from *config*.

    Pool-related parameters are only forwarded for connection-pooling
    backends (e.g. PostgreSQL via asyncpg).  SQLite/aiosqlite does not
    support them, so they are omitted automatically.
    """
    kwargs: dict = {
        "echo": config.echo,
    }

    if not _is_sqlite(config.url):
        kwargs["pool_size"] = config.pool_size
        kwargs["max_overflow"] = config.max_overflow
        kwargs["pool_timeout"] = config.pool_timeout

    return create_async_engine(config.url, **kwargs)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory bound to *engine*."""
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a transactional async database session.

    The session is committed on successful exit and rolled back if an
    exception propagates.

    Usage in generated projects::

        # In dependencies.py
        async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
            async with session_factory() as session:
                yield session
    """
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
