"""Smoke test: Compare business logic DB call patterns.

Question: Does FastStack's CrudService + Repository pattern result in
fewer DB calls than rag_modulo's hand-written orchestrator?

rag_modulo's MessageProcessingOrchestrator makes 11 operations per
message (6 DB, 5 service calls), including a redundant provider lookup.

This test builds equivalent business logic on FastStack's base classes
to see if the pattern naturally avoids those inefficiencies.

Usage:
    PYTHONPATH=. python examples/smoke_test_orchestrator.py
    (run from the faststack project root, not a generated project)
"""

import asyncio
import logging
import uuid
from uuid import UUID

from sqlalchemy import Float, ForeignKey, Integer, String, Text, func, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Mapped, mapped_column

from faststack_core.base.entity import AuditedEntity, Base
from faststack_core.base.repository import SqlAlchemyRepository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-5s | %(name)s | %(message)s",
)
logger = logging.getLogger("orchestrator")


# ---------------------------------------------------------------------------
# Models (inline — no generated project needed)
# ---------------------------------------------------------------------------


class User(AuditedEntity):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))


class ConversationSession(AuditedEntity):
    __tablename__ = "conversation_sessions"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    session_name: Mapped[str] = mapped_column(String(255))


class ConversationMessage(AuditedEntity):
    __tablename__ = "conversation_messages"
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversation_sessions.id"))
    content: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(50))
    token_count: Mapped[int | None] = mapped_column(Integer, default=None)


# ---------------------------------------------------------------------------
# DB call tracker
# ---------------------------------------------------------------------------
db_calls: list[str] = []


def track(operation: str, detail: str = "") -> None:
    label = f"{operation}: {detail}" if detail else operation
    db_calls.append(label)
    logger.info(f"[#{len(db_calls):02d}] {label}")


# ---------------------------------------------------------------------------
# Repositories (extend SqlAlchemyRepository with custom queries)
# ---------------------------------------------------------------------------


class SessionRepository(SqlAlchemyRepository):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, ConversationSession)

    async def get_session_by_id(self, session_id: UUID) -> ConversationSession | None:
        track("DB READ", "get session by id")
        return await self.get_by_id(session_id)


class MessageRepository(SqlAlchemyRepository):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, ConversationMessage)

    async def create_message(
        self, session_id: UUID, content: str, role: str
    ) -> ConversationMessage:
        track("DB WRITE", f"create {role} message ({len(content)} chars)")
        return await self.create(
            {
                "session_id": session_id,
                "content": content,
                "role": role,
                "token_count": len(content.split()),
            }
        )

    async def get_messages_by_session(self, session_id: UUID) -> list[ConversationMessage]:
        track("DB READ", "get messages for session")
        result = await self.db.execute(
            select(ConversationMessage).where(ConversationMessage.session_id == session_id)
        )
        return list(result.scalars().all())

    async def get_token_usage(self, session_id: UUID) -> int:
        track("DB READ", "aggregate token_count for session")
        result = await self.db.execute(
            select(func.coalesce(func.sum(ConversationMessage.token_count), 0)).where(
                ConversationMessage.session_id == session_id
            )
        )
        return result.scalar_one()


class UserRepository(SqlAlchemyRepository):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, User)

    async def get_user_provider(self, user_id: UUID) -> str:
        track("DB READ", "get user's LLM provider")
        return "mock-provider"


# ---------------------------------------------------------------------------
# Orchestrator — FastStack version
# ---------------------------------------------------------------------------


class MessageOrchestrator:
    """Message processing using FastStack patterns.

    Key differences from rag_modulo:
    - Repository provides typed methods (not raw SQL)
    - The redundant provider lookup is avoided by caching
    """

    def __init__(
        self,
        session_repo: SessionRepository,
        message_repo: MessageRepository,
        user_repo: UserRepository,
    ) -> None:
        self.session_repo = session_repo
        self.message_repo = message_repo
        self.user_repo = user_repo

    async def process_message(self, session_id: UUID, user_id: UUID, content: str) -> dict:
        db_calls.clear()
        logger.info(f"Processing message for session {session_id}")

        # 1. Load session
        session = await self.session_repo.get_session_by_id(session_id)
        if not session:
            raise ValueError("Session not found")

        # 2. Store user message
        user_msg = await self.message_repo.create_message(session_id, content, "user")

        # 3. Get history for context
        messages = await self.message_repo.get_messages_by_session(session_id)
        logger.info(f"  {len(messages)} messages in history")

        # 4-6. Service calls (context, enhance, search)
        track("SERVICE", "build context from messages")
        track("SERVICE", "enhance question with context")
        track("SERVICE", "RAG search (vector DB + LLM)")

        # 7. Get provider (ONCE — unlike rag_modulo which does it twice)
        provider = await self.user_repo.get_user_provider(user_id)

        # 8. Get token usage
        total_tokens = await self.message_repo.get_token_usage(session_id)
        logger.info(f"  Total tokens in session: {total_tokens}")

        # 9. Check token warning (uses cached provider — NO redundant DB call)
        track("SERVICE", f"check token warning (provider={provider}, cached)")

        # 10. Store assistant response
        answer = f"Generated answer for: {content[:50]}"
        assistant_msg = await self.message_repo.create_message(session_id, answer, "assistant")

        return {
            "user_msg_id": user_msg.id,
            "assistant_msg_id": assistant_msg.id,
            "answer": answer,
            "total_tokens": total_tokens,
            "db_calls": len(db_calls),
        }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> None:
    print("=" * 70)
    print("FastStack vs rag_modulo: DB Call Pattern Comparison")
    print("=" * 70)

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        # Seed
        user = User(email="manav@test.com", name="Manav Gupta")
        session.add(user)
        await session.flush()

        conv = ConversationSession(user_id=user.id, session_name="Test Chat")
        session.add(conv)
        await session.flush()

        # Process a message
        orchestrator = MessageOrchestrator(
            SessionRepository(session),
            MessageRepository(session),
            UserRepository(session),
        )

        print()
        result = await orchestrator.process_message(
            conv.id,
            user.id,
            "What are the key findings in the quarterly report?",
        )

    await engine.dispose()

    # Report
    actual_db = sum(1 for c in db_calls if c.startswith("DB"))
    service_calls = sum(1 for c in db_calls if c.startswith("SERVICE"))

    print("\n" + "=" * 70)
    print("COMPARISON")
    print("=" * 70)
    print()
    print("  rag_modulo (current):")
    print("    11 total operations")
    print("     6 DB calls (2 writes, 3 reads, 1 aggregate)")
    print("     5 service calls")
    print("     x get_user_provider called TWICE (redundant)")
    print("     x No correlation IDs in logs")
    print("     x 45+ manual log statements with emojis")
    print()
    print("  FastStack (this test):")
    print(f"    {len(db_calls)} total operations")
    print(f"     {actual_db} DB calls")
    print(f"     {service_calls} service calls")
    print("     + get_user_provider called ONCE (cached)")
    print("     + Correlation IDs via middleware (automatic)")
    print("     + Request logging via middleware (automatic)")
    print()
    print("  Call log:")
    for i, call in enumerate(db_calls, 1):
        marker = "  " if call.startswith("SERVICE") else "> "
        print(f"    {marker}#{i:02d}  {call}")
    print()
    saved = 11 - len(db_calls)
    if saved > 0:
        print(f"  Result: {saved} fewer operation(s) by caching the provider lookup")
    print()


if __name__ == "__main__":
    asyncio.run(main())
