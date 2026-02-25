"""Tests for the seed script — entity counts, relationships, idempotency."""

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.models import (
    Client,
    EntryTypeEnum,
    Exercise,
    InjuryFlag,
    Session,
    SessionEntry,
    SessionPlan,
    Trainer,
)
from app.seed import seed

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(loop_scope="session")
async def seeded_db(db_session):
    """Run the seed script and return the db session."""
    await seed(db_session, commit=False)
    return db_session


# --- Basic counts ---


async def test_seed_runs_without_error(seeded_db):
    """Seed completes on an empty database without raising."""
    # If we got here, seed ran successfully
    result = await seeded_db.execute(select(func.count()).select_from(Trainer))
    assert result.scalar_one() == 1


async def test_entity_counts(seeded_db):
    """Verify correct counts: 1 trainer, 5 clients, 34 sessions, 6 plans, 4 injuries."""
    db = seeded_db

    trainer_count = (await db.execute(select(func.count()).select_from(Trainer))).scalar_one()
    client_count = (await db.execute(select(func.count()).select_from(Client))).scalar_one()
    session_count = (await db.execute(select(func.count()).select_from(Session))).scalar_one()
    plan_count = (await db.execute(select(func.count()).select_from(SessionPlan))).scalar_one()
    injury_count = (await db.execute(select(func.count()).select_from(InjuryFlag))).scalar_one()

    assert trainer_count == 1
    assert client_count == 5
    assert session_count == 34  # 1 + 3 + 5 + 10 + 15
    assert plan_count == 6  # Aisha: 1, Jake: 2, Elena: 3
    assert injury_count == 4  # Marcus: 1, Jake: 1, Elena: 2


async def test_exercise_table_populated(seeded_db):
    """Exercise reference table matches exercise_db.json count."""
    db = seeded_db
    from app.services.transcription import load_exercise_db

    expected_count = len(load_exercise_db())
    count = (await db.execute(select(func.count()).select_from(Exercise))).scalar_one()
    assert count == expected_count


async def test_session_entry_count_and_types(seeded_db):
    """Both exercise_card and observation_card entries exist."""
    db = seeded_db

    total = (await db.execute(select(func.count()).select_from(SessionEntry))).scalar_one()
    assert total > 0

    exercise_count = (await db.execute(
        select(func.count()).select_from(SessionEntry)
        .where(SessionEntry.entry_type == EntryTypeEnum.exercise_card)
    )).scalar_one()
    observation_count = (await db.execute(
        select(func.count()).select_from(SessionEntry)
        .where(SessionEntry.entry_type == EntryTypeEnum.observation_card)
    )).scalar_one()

    assert exercise_count > 0
    assert observation_count > 0
    assert exercise_count + observation_count == total


# --- Relationships ---


async def test_session_plans_linked_to_correct_clients(seeded_db):
    """Aisha: 1 plan, Jake: 2 plans, Elena: 3 plans."""
    db = seeded_db

    # Get clients by name
    clients = (await db.execute(select(Client).order_by(Client.name))).scalars().all()
    client_by_name = {c.name: c for c in clients}

    aisha = client_by_name["Aisha Patel"]
    jake = client_by_name["Jake Morrison"]
    elena = client_by_name["Elena Vasquez"]

    for client, expected in [(aisha, 1), (jake, 2), (elena, 3)]:
        count = (await db.execute(
            select(func.count()).select_from(SessionPlan)
            .where(SessionPlan.client_id == client.id)
        )).scalar_one()
        assert count == expected, f"{client.name} should have {expected} plans, got {count}"


async def test_sessions_with_plans_have_plan_id(seeded_db):
    """Sessions linked to plans have non-null plan_id."""
    db = seeded_db

    sessions_with_plan = (await db.execute(
        select(func.count()).select_from(Session)
        .where(Session.plan_id.is_not(None))
    )).scalar_one()

    # Aisha: 3 sessions with plan, Jake: 10 with plan, Elena: 15 with plan
    assert sessions_with_plan == 28


async def test_injury_flags_reference_valid_sessions(seeded_db):
    """Every injury flag points to a real session owned by the correct client."""
    db = seeded_db

    injuries = (await db.execute(select(InjuryFlag))).scalars().all()
    assert len(injuries) == 4

    for injury in injuries:
        session = (await db.execute(
            select(Session).where(Session.id == injury.session_id)
        )).scalar_one_or_none()
        assert session is not None, f"Injury {injury.id} references non-existent session"
        assert session.client_id == injury.client_id, (
            f"Injury client_id {injury.client_id} doesn't match session client_id {session.client_id}"
        )


async def test_elena_has_resolved_injury(seeded_db):
    """Elena has exactly 1 resolved injury flag (left shoulder)."""
    db = seeded_db

    elena = (await db.execute(
        select(Client).where(Client.name == "Elena Vasquez")
    )).scalar_one()

    elena_injuries = (await db.execute(
        select(InjuryFlag).where(InjuryFlag.client_id == elena.id)
    )).scalars().all()

    assert len(elena_injuries) == 2

    resolved = [i for i in elena_injuries if i.resolved]
    active = [i for i in elena_injuries if not i.resolved]

    assert len(resolved) == 1
    assert resolved[0].body_part == "left shoulder"
    assert resolved[0].resolved_at is not None

    assert len(active) == 1
    assert active[0].body_part == "right hip"


async def test_idempotent_seed_twice(seeded_db):
    """Running seed twice produces the same counts — no duplication."""
    db = seeded_db

    # Seed again (idempotent — truncates first)
    await seed(db, commit=False)

    trainer_count = (await db.execute(select(func.count()).select_from(Trainer))).scalar_one()
    client_count = (await db.execute(select(func.count()).select_from(Client))).scalar_one()
    session_count = (await db.execute(select(func.count()).select_from(Session))).scalar_one()
    exercise_count = (await db.execute(select(func.count()).select_from(Exercise))).scalar_one()
    injury_count = (await db.execute(select(func.count()).select_from(InjuryFlag))).scalar_one()

    assert trainer_count == 1
    assert client_count == 5
    assert session_count == 34
    from app.services.transcription import load_exercise_db

    assert exercise_count == len(load_exercise_db())
    assert injury_count == 4


async def test_session_counts_per_client(seeded_db):
    """Sarah: 1, Marcus: 3, Aisha: 5, Jake: 10, Elena: 15."""
    db = seeded_db

    expected = {
        "Sarah Chen": 1,
        "Marcus Johnson": 3,
        "Aisha Patel": 5,
        "Jake Morrison": 10,
        "Elena Vasquez": 15,
    }

    clients = (await db.execute(select(Client))).scalars().all()
    for client in clients:
        count = (await db.execute(
            select(func.count()).select_from(Session)
            .where(Session.client_id == client.id)
        )).scalar_one()
        assert count == expected[client.name], (
            f"{client.name}: expected {expected[client.name]} sessions, got {count}"
        )
