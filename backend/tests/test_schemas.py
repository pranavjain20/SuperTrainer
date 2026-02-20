import uuid

import pytest
from pydantic import ValidationError

from app.schemas import (
    ClientCreate,
    ExerciseLogCreate,
    InjuryFlagCreate,
    SessionCreate,
    SessionUpdate,
    TrainerCreate,
)


def test_client_create_requires_name():
    with pytest.raises(ValidationError):
        ClientCreate()


def test_client_create_valid():
    c = ClientCreate(name="John Doe", email="john@test.com", goals=["strength"])
    assert c.name == "John Doe"
    assert c.goals == ["strength"]


def test_client_create_rejects_empty_name():
    with pytest.raises(ValidationError):
        ClientCreate(name="")


def test_session_create_requires_fields():
    with pytest.raises(ValidationError):
        SessionCreate()


def test_session_create_valid():
    s = SessionCreate(client_id=uuid.uuid4(), started_at="2026-02-19T10:00:00Z")
    assert s.client_id is not None


def test_injury_flag_pain_level_min():
    with pytest.raises(ValidationError):
        InjuryFlagCreate(
            client_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            body_part="knee",
            pain_level=0,
        )


def test_injury_flag_pain_level_max():
    with pytest.raises(ValidationError):
        InjuryFlagCreate(
            client_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            body_part="knee",
            pain_level=11,
        )


def test_injury_flag_valid():
    flag = InjuryFlagCreate(
        client_id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        body_part="left shoulder",
        pain_level=5,
        description="Dull ache during overhead press",
    )
    assert flag.pain_level == 5
    assert flag.exercise_log_id is None


def test_trainer_create_requires_email_and_name():
    with pytest.raises(ValidationError):
        TrainerCreate()


# --- SessionUpdate ---


def test_session_update_all_fields_optional():
    s = SessionUpdate()
    assert s.ended_at is None
    assert s.duration_minutes is None
    assert s.raw_transcript is None
    assert s.processing_status is None
    assert s.trainer_edited is None


def test_session_update_valid():
    s = SessionUpdate(
        duration_minutes=60,
        processing_status="completed",
        trainer_edited=True,
    )
    assert s.duration_minutes == 60
    assert s.processing_status.value == "completed"
    assert s.trainer_edited is True


def test_session_update_invalid_processing_status():
    with pytest.raises(ValidationError):
        SessionUpdate(processing_status="bogus")


# --- ExerciseLogCreate ---


def test_exercise_log_create_requires_fields():
    with pytest.raises(ValidationError):
        ExerciseLogCreate()


def test_exercise_log_create_valid():
    e = ExerciseLogCreate(
        session_id=uuid.uuid4(),
        exercise_name="Bench Press",
        sets=[{"set": 1, "weight_kg": 80, "reps": 8}],
    )
    assert e.exercise_name == "Bench Press"
    assert len(e.sets) == 1


def test_exercise_log_create_minimal():
    e = ExerciseLogCreate(session_id=uuid.uuid4(), exercise_name="Squat")
    assert e.sets is None
    assert e.total_volume_kg is None
    assert e.form_notes is None


def test_exercise_log_create_rejects_empty_name():
    with pytest.raises(ValidationError):
        ExerciseLogCreate(session_id=uuid.uuid4(), exercise_name="")
