import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

pytestmark = pytest.mark.asyncio(loop_scope="session")

from app.models import (
    Client,
    ClientAnalysis,
    Exercise,
    ExerciseLog,
    InjuryFlag,
    ProcessingStatusEnum,
    RiskLevelEnum,
    Session,
    TierEnum,
    Trainer,
)


def _utcnow():
    return datetime.now(timezone.utc)


async def _create_trainer(db_session, **overrides):
    defaults = {"email": f"trainer-{uuid.uuid4().hex[:8]}@test.com", "name": "Test Trainer"}
    defaults.update(overrides)
    trainer = Trainer(**defaults)
    db_session.add(trainer)
    await db_session.flush()
    return trainer


async def _create_client(db_session, trainer_id, **overrides):
    defaults = {"trainer_id": trainer_id, "name": "Test Client"}
    defaults.update(overrides)
    client = Client(**defaults)
    db_session.add(client)
    await db_session.flush()
    return client


async def _create_session(db_session, trainer_id, client_id, **overrides):
    defaults = {"trainer_id": trainer_id, "client_id": client_id, "started_at": _utcnow()}
    defaults.update(overrides)
    session = Session(**defaults)
    db_session.add(session)
    await db_session.flush()
    return session


# --- Trainer ---


async def test_create_trainer(db_session):
    trainer = await _create_trainer(db_session)
    result = await db_session.get(Trainer, trainer.id)
    assert result is not None
    assert result.email == trainer.email
    assert result.tier == TierEnum.free


async def test_trainer_unique_email(db_session):
    email = "duplicate@test.com"
    await _create_trainer(db_session, email=email)
    nested = await db_session.begin_nested()
    with pytest.raises(IntegrityError):
        await _create_trainer(db_session, email=email)
    await nested.rollback()


# --- Client ---


async def test_create_client_linked_to_trainer(db_session):
    trainer = await _create_trainer(db_session)
    client = await _create_client(db_session, trainer.id, goals=["strength", "mobility"])
    result = await db_session.get(Client, client.id)
    assert result is not None
    assert result.trainer_id == trainer.id
    assert result.goals == ["strength", "mobility"]
    assert result.archived is False


async def test_client_requires_valid_trainer(db_session):
    fake_id = uuid.uuid4()
    nested = await db_session.begin_nested()
    with pytest.raises(IntegrityError):
        await _create_client(db_session, fake_id)
    await nested.rollback()


# --- Session ---


async def test_create_session(db_session):
    trainer = await _create_trainer(db_session)
    client = await _create_client(db_session, trainer.id)
    session = await _create_session(db_session, trainer.id, client.id)
    result = await db_session.get(Session, session.id)
    assert result is not None
    assert result.processing_status == ProcessingStatusEnum.pending
    assert result.trainer_edited is False


async def test_session_requires_valid_client(db_session):
    trainer = await _create_trainer(db_session)
    nested = await db_session.begin_nested()
    with pytest.raises(IntegrityError):
        await _create_session(db_session, trainer.id, uuid.uuid4())
    await nested.rollback()


# --- ExerciseLog ---


async def test_create_exercise_log_with_jsonb(db_session):
    trainer = await _create_trainer(db_session)
    client = await _create_client(db_session, trainer.id)
    session = await _create_session(db_session, trainer.id, client.id)

    sets_data = [
        {"set_number": 1, "weight_kg": 80, "reps": 8, "rpe": 7},
        {"set_number": 2, "weight_kg": 80, "reps": 7, "rpe": 8},
    ]
    log = ExerciseLog(
        session_id=session.id,
        client_id=client.id,
        exercise_name="Barbell Back Squat",
        exercise_canonical="barbell_back_squat",
        sets=sets_data,
        total_volume_kg=1200.0,
        form_notes=["depth good", "knees caving on set 2"],
        cues_given=["push knees out"],
    )
    db_session.add(log)
    await db_session.flush()

    result = await db_session.get(ExerciseLog, log.id)
    assert result is not None
    assert result.sets == sets_data
    assert result.form_notes == ["depth good", "knees caving on set 2"]


# --- InjuryFlag ---


async def test_create_injury_flag(db_session):
    trainer = await _create_trainer(db_session)
    client = await _create_client(db_session, trainer.id)
    session = await _create_session(db_session, trainer.id, client.id)

    flag = InjuryFlag(
        client_id=client.id,
        session_id=session.id,
        body_part="left knee",
        pain_level=6,
        description="Sharp pain during deep squat",
    )
    db_session.add(flag)
    await db_session.flush()

    result = await db_session.get(InjuryFlag, flag.id)
    assert result is not None
    assert result.body_part == "left knee"
    assert result.pain_level == 6
    assert result.exercise_log_id is None
    assert result.resolved is False


# --- ClientAnalysis ---


async def test_create_client_analysis(db_session):
    trainer = await _create_trainer(db_session)
    client = await _create_client(db_session, trainer.id)

    analysis = ClientAnalysis(
        client_id=client.id,
        total_sessions=15,
        injury_risk_score=42.5,
        injury_risk_level=RiskLevelEnum.medium,
        risk_factors=["recurring knee pain", "rapid volume increase"],
    )
    db_session.add(analysis)
    await db_session.flush()

    result = await db_session.get(ClientAnalysis, analysis.id)
    assert result is not None
    assert result.total_sessions == 15
    assert result.injury_risk_level == RiskLevelEnum.medium
    assert result.risk_factors == ["recurring knee pain", "rapid volume increase"]


# --- Exercise ---


async def test_create_exercise_with_aliases(db_session):
    exercise = Exercise(
        canonical_name="barbell_back_squat",
        aliases=["back squat", "squat", "BB squat"],
        category="compound",
        primary_muscles=["quadriceps", "glutes", "hamstrings"],
        equipment=["barbell", "squat rack"],
        difficulty="intermediate",
    )
    db_session.add(exercise)
    await db_session.flush()

    result = await db_session.get(Exercise, exercise.id)
    assert result is not None
    assert result.canonical_name == "barbell_back_squat"
    assert "back squat" in result.aliases


async def test_exercise_unique_canonical_name(db_session):
    name = "unique_exercise"
    e1 = Exercise(canonical_name=name)
    db_session.add(e1)
    await db_session.flush()

    nested = await db_session.begin_nested()
    with pytest.raises(IntegrityError):
        e2 = Exercise(canonical_name=name)
        db_session.add(e2)
        await db_session.flush()
    await nested.rollback()


# --- Enum validation ---


async def test_processing_status_enum(db_session):
    trainer = await _create_trainer(db_session)
    client = await _create_client(db_session, trainer.id)
    session = await _create_session(
        db_session, trainer.id, client.id, processing_status=ProcessingStatusEnum.completed
    )
    result = await db_session.get(Session, session.id)
    assert result.processing_status == ProcessingStatusEnum.completed


async def test_tier_enum(db_session):
    trainer = await _create_trainer(db_session, tier=TierEnum.trainer_pro)
    result = await db_session.get(Trainer, trainer.id)
    assert result.tier == TierEnum.trainer_pro
