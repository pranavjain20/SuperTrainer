import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import Trainer

TEST_DATABASE_URL = settings.test_database_url


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def engine():
    """Create engine and tables once for the entire test session."""
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with eng.begin() as conn:
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
            "TRUNCATE TABLE injury_flags, exercise_logs, sessions, "
            "client_analysis, clients, trainers, exercises CASCADE"
        ))


@pytest_asyncio.fixture(loop_scope="session")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """FastAPI test client with overridden DB dependency."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Reset the temp trainer ID cache
    from app.api import clients as clients_module
    clients_module.TEMP_TRAINER_ID = None

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(loop_scope="session")
async def seed_trainer(db_session: AsyncSession) -> Trainer:
    """Create a trainer for endpoint tests."""
    trainer = Trainer(
        email=f"test-trainer-{uuid.uuid4().hex[:8]}@test.com",
        name="Test Trainer",
    )
    db_session.add(trainer)
    await db_session.commit()
    await db_session.refresh(trainer)
    return trainer
