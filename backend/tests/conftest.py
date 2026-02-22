import uuid
from collections.abc import AsyncGenerator

import httpx
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import Base
from app.models import Client, Session, Trainer

TEST_DATABASE_URL = settings.test_database_url


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def engine():
    """Create engine and tables once for the entire test session."""
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with eng.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Fresh session per test. Truncates all tables after each test."""
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    # Clean up all data after each test
    async with engine.begin() as conn:
        await conn.execute(text(
            "TRUNCATE TABLE brain_messages, brain_conversations, injury_flags, "
            "session_entries, sessions, session_plans, client_analysis, "
            "clients, trainers, exercises CASCADE"
        ))


@pytest_asyncio.fixture(loop_scope="session")
async def client(db_session: AsyncSession) -> AsyncGenerator[httpx.AsyncClient, None]:
    """HTTP test client. Overrides get_db so handlers share the test db_session."""
    from app.database import get_db
    from app.main import app

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(loop_scope="session")
async def trainer_for_api(db_session: AsyncSession) -> AsyncGenerator[Trainer, None]:
    """Create a trainer and set TEMP_TRAINER_ID so API endpoints work."""
    from app.api import dependencies

    trainer = Trainer(email=f"api-trainer-{uuid.uuid4().hex[:8]}@test.com", name="API Trainer")
    db_session.add(trainer)
    await db_session.flush()
    dependencies.TEMP_TRAINER_ID = trainer.id
    yield trainer
    dependencies.TEMP_TRAINER_ID = None


@pytest_asyncio.fixture(loop_scope="session")
async def trainer_and_client(
    db_session: AsyncSession, trainer_for_api: Trainer,
) -> tuple[Trainer, Client]:
    """Create a trainer (via trainer_for_api) + client for session tests."""
    db_client = Client(trainer_id=trainer_for_api.id, name="Test Client")
    db_session.add(db_client)
    await db_session.flush()
    return trainer_for_api, db_client


@pytest_asyncio.fixture(loop_scope="session")
async def trainer_client_session(
    db_session: AsyncSession, trainer_for_api: Trainer,
) -> tuple[Trainer, Client, Session]:
    """Create trainer + client + session for entry tests."""
    from datetime import datetime, timezone

    db_client = Client(trainer_id=trainer_for_api.id, name="Entry Test Client")
    db_session.add(db_client)
    await db_session.flush()

    db_session_obj = Session(
        trainer_id=trainer_for_api.id,
        client_id=db_client.id,
        started_at=datetime(2026, 2, 22, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(db_session_obj)
    await db_session.flush()

    return trainer_for_api, db_client, db_session_obj
