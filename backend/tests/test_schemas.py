import types
import uuid
from datetime import date, datetime

import pytest
from pydantic import ValidationError

from app.models import EntryTypeEnum, MessageRoleEnum, ProcessingStatusEnum, RiskLevelEnum, TierEnum
from app.schemas import (
    BrainConversationCreate,
    BrainConversationUpdate,
    BrainMessageCreate,
    BrainMessageResponse,
    ClientAnalysisResponse,
    ClientCreate,
    ClientUpdate,
    ExerciseCreate,
    InjuryFlagCreate,
    InjuryFlagUpdate,
    SessionCreate,
    SessionEntryCreate,
    SessionEntryResponse,
    SessionEntryUpdate,
    SessionPlanCreate,
    SessionPlanUpdate,
    SessionResponse,
    SessionUpdate,
    TrainerCreate,
)


# --- Trainer ---


def test_trainer_create_requires_email_and_name():
    with pytest.raises(ValidationError):
        TrainerCreate()


def test_trainer_create_valid():
    t = TrainerCreate(email="coach@gym.com", name="Coach Mike")
    assert t.email == "coach@gym.com"
    assert t.name == "Coach Mike"
    assert t.phone is None
    assert t.tier == TierEnum.free


def test_trainer_create_rejects_empty_email():
    with pytest.raises(ValidationError):
        TrainerCreate(email="", name="Coach")


def test_trainer_create_rejects_empty_name():
    with pytest.raises(ValidationError):
        TrainerCreate(email="valid@test.com", name="")


# --- Client ---


def test_client_create_requires_name():
    with pytest.raises(ValidationError):
        ClientCreate()


def test_client_create_valid():
    c = ClientCreate(name="John Doe", email="john@test.com", goals=["strength"])
    assert c.name == "John Doe"
    assert c.email == "john@test.com"
    assert c.goals == ["strength"]
    assert c.phone is None
    assert c.birth_date is None
    assert c.training_start_date is None
    assert c.injury_history is None


def test_client_create_rejects_empty_name():
    with pytest.raises(ValidationError):
        ClientCreate(name="")


def test_client_update_all_optional():
    u = ClientUpdate()
    assert u.name is None
    assert u.email is None
    assert u.phone is None
    assert u.birth_date is None
    assert u.training_start_date is None
    assert u.goals is None
    assert u.injury_history is None
    assert u.archived is None


def test_client_update_rejects_empty_name():
    with pytest.raises(ValidationError):
        ClientUpdate(name="")


# --- Session ---


def test_session_create_requires_client_id_and_started_at():
    with pytest.raises(ValidationError):
        SessionCreate()


def test_session_create_valid():
    s = SessionCreate(client_id=uuid.uuid4(), started_at="2026-02-19T10:00:00Z")
    assert s.client_id is not None
    assert s.scheduled_for is None
    assert s.plan_id is None


def test_session_create_with_scheduled_for_and_plan_id():
    plan_id = uuid.uuid4()
    s = SessionCreate(
        client_id=uuid.uuid4(),
        started_at="2026-02-19T10:00:00Z",
        scheduled_for="2026-02-20T09:00:00Z",
        plan_id=plan_id,
    )
    assert s.scheduled_for is not None
    assert s.plan_id == plan_id


def test_session_update_all_optional():
    s = SessionUpdate()
    assert s.ended_at is None
    assert s.scheduled_for is None
    assert s.duration_minutes is None
    assert s.raw_transcript is None
    assert s.processing_status is None
    assert s.trainer_edited is None


def test_session_update_invalid_processing_status():
    with pytest.raises(ValidationError):
        SessionUpdate(processing_status="bogus")


# --- SessionEntry ---


def test_session_entry_create_exercise_card_valid():
    e = SessionEntryCreate(
        entry_type=EntryTypeEnum.exercise_card,
        sequence_order=1,
        exercise_name="Bench Press",
        sets=[{"set": 1, "weight_kg": 80, "reps": 8}],
        total_volume_kg=640.0,
        form_notes=["Good depth"],
        cues_given=["Drive through heels"],
    )
    assert e.exercise_name == "Bench Press"
    assert e.entry_type == EntryTypeEnum.exercise_card
    assert len(e.sets) == 1
    assert e.observation_text is None


def test_session_entry_create_exercise_card_minimal():
    e = SessionEntryCreate(
        entry_type=EntryTypeEnum.exercise_card,
        sequence_order=1,
        exercise_name="Squat",
    )
    assert e.sets is None
    assert e.total_volume_kg is None
    assert e.form_notes is None
    assert e.cues_given is None


def test_session_entry_create_sequence_order_optional():
    e = SessionEntryCreate(
        entry_type=EntryTypeEnum.exercise_card,
        exercise_name="Squat",
    )
    assert e.sequence_order is None


def test_session_entry_create_exercise_card_requires_exercise_name():
    with pytest.raises(ValidationError, match="exercise_name is required"):
        SessionEntryCreate(
            entry_type=EntryTypeEnum.exercise_card,
            sequence_order=1,
        )


def test_session_entry_create_exercise_card_rejects_observation_text():
    with pytest.raises(ValidationError, match="observation_text must be None"):
        SessionEntryCreate(
            entry_type=EntryTypeEnum.exercise_card,
            sequence_order=1,
            exercise_name="Squat",
            observation_text="Some observation",
        )


def test_session_entry_create_observation_card_valid():
    e = SessionEntryCreate(
        entry_type=EntryTypeEnum.observation_card,
        sequence_order=2,
        observation_text="Client seemed fatigued in the last set",
        flag_color="yellow",
        flag_reason="fatigue",
    )
    assert e.observation_text == "Client seemed fatigued in the last set"
    assert e.entry_type == EntryTypeEnum.observation_card
    assert e.exercise_name is None
    assert e.sets is None


def test_session_entry_create_observation_card_requires_observation_text():
    with pytest.raises(ValidationError, match="observation_text is required"):
        SessionEntryCreate(
            entry_type=EntryTypeEnum.observation_card,
            sequence_order=1,
        )


def test_session_entry_create_observation_card_rejects_exercise_name():
    with pytest.raises(ValidationError, match="exercise_name must be None"):
        SessionEntryCreate(
            entry_type=EntryTypeEnum.observation_card,
            sequence_order=1,
            observation_text="Some observation",
            exercise_name="Squat",
        )


def test_session_entry_create_observation_card_rejects_sets():
    with pytest.raises(ValidationError, match="sets must be None"):
        SessionEntryCreate(
            entry_type=EntryTypeEnum.observation_card,
            sequence_order=1,
            observation_text="Some observation",
            sets=[{"set": 1}],
        )


def test_session_entry_create_requires_fields():
    with pytest.raises(ValidationError):
        SessionEntryCreate()


def test_session_entry_create_rejects_empty_exercise_name():
    with pytest.raises(ValidationError):
        SessionEntryCreate(
            entry_type=EntryTypeEnum.exercise_card,
            sequence_order=1,
            exercise_name="",
        )


def test_session_entry_create_sequence_order_must_be_positive():
    with pytest.raises(ValidationError):
        SessionEntryCreate(
            entry_type=EntryTypeEnum.exercise_card,
            sequence_order=0,
            exercise_name="Squat",
        )


def test_session_entry_create_total_volume_kg_non_negative():
    with pytest.raises(ValidationError):
        SessionEntryCreate(
            entry_type=EntryTypeEnum.exercise_card,
            sequence_order=1,
            exercise_name="Squat",
            total_volume_kg=-1.0,
        )


def test_session_entry_create_sets_rejects_bare_dict():
    """v1 bug: sets was list | dict | None. Now list[dict] | None — bare dict must fail."""
    with pytest.raises(ValidationError):
        SessionEntryCreate(
            entry_type=EntryTypeEnum.exercise_card,
            sequence_order=1,
            exercise_name="Squat",
            sets={"set": 1, "weight_kg": 80, "reps": 8},
        )


def test_session_entry_update_all_optional():
    u = SessionEntryUpdate()
    assert u.entry_type is None
    assert u.sequence_order is None
    assert u.exercise_name is None
    assert u.exercise_canonical is None
    assert u.sets is None
    assert u.total_volume_kg is None
    assert u.form_notes is None
    assert u.cues_given is None
    assert u.cue_effectiveness is None
    assert u.observation_text is None
    assert u.attached_to_set is None
    assert u.flag_color is None
    assert u.flag_reason is None
    assert u.performed_at is None


def test_session_entry_update_rejects_invalid_constraints():
    with pytest.raises(ValidationError):
        SessionEntryUpdate(sequence_order=0)
    with pytest.raises(ValidationError):
        SessionEntryUpdate(exercise_name="")
    with pytest.raises(ValidationError):
        SessionEntryUpdate(total_volume_kg=-1.0)


def test_session_entry_update_rejects_cross_type_exercise_card():
    """PATCH with entry_type=exercise_card should reject observation fields."""
    with pytest.raises(ValidationError, match="observation_text must be None"):
        SessionEntryUpdate(
            entry_type=EntryTypeEnum.exercise_card,
            observation_text="bad field",
        )


def test_session_entry_update_rejects_attached_to_set_on_exercise_card():
    """exercise_card entries should never have attached_to_set."""
    with pytest.raises(ValidationError, match="attached_to_set must be None"):
        SessionEntryUpdate(
            entry_type=EntryTypeEnum.exercise_card,
            attached_to_set=2,
        )


def test_session_entry_update_rejects_cross_type_observation_card():
    """PATCH with entry_type=observation_card should reject exercise fields."""
    with pytest.raises(ValidationError, match="exercise_name must be None"):
        SessionEntryUpdate(
            entry_type=EntryTypeEnum.observation_card,
            exercise_name="Squat",
        )


def test_session_entry_update_allows_fields_without_entry_type():
    """When entry_type is not in the update, cross-field validation is skipped."""
    u = SessionEntryUpdate(exercise_name="Squat", observation_text="note")
    assert u.exercise_name == "Squat"
    assert u.observation_text == "note"


def test_session_entry_create_exercise_card_rejects_attached_to_set():
    """exercise_card entries should reject attached_to_set."""
    with pytest.raises(ValidationError, match="attached_to_set must be None"):
        SessionEntryCreate(
            entry_type=EntryTypeEnum.exercise_card,
            exercise_name="Squat",
            attached_to_set=3,
        )


def test_session_entry_create_rejects_empty_exercise_canonical():
    """exercise_canonical should reject empty strings if provided."""
    with pytest.raises(ValidationError):
        SessionEntryCreate(
            entry_type=EntryTypeEnum.exercise_card,
            exercise_name="Squat",
            exercise_canonical="",
        )


def test_session_entry_update_rejects_empty_exercise_canonical():
    """exercise_canonical should reject empty strings on update too."""
    with pytest.raises(ValidationError):
        SessionEntryUpdate(exercise_canonical="")


# --- SessionPlan ---


def test_session_plan_create_requires_fields():
    with pytest.raises(ValidationError):
        SessionPlanCreate()


def test_session_plan_create_valid():
    p = SessionPlanCreate(
        client_id=uuid.uuid4(),
        plan_text="Focus on upper body, 4x8 bench press",
        planned_for_date=date(2026, 2, 25),
    )
    assert p.plan_text == "Focus on upper body, 4x8 bench press"
    assert p.planned_for_date == date(2026, 2, 25)


def test_session_plan_create_rejects_empty_plan_text():
    with pytest.raises(ValidationError):
        SessionPlanCreate(client_id=uuid.uuid4(), plan_text="")


def test_session_plan_update_all_optional():
    u = SessionPlanUpdate()
    assert u.plan_text is None
    assert u.planned_for_date is None


def test_session_plan_update_rejects_empty_plan_text():
    with pytest.raises(ValidationError):
        SessionPlanUpdate(plan_text="")


# --- InjuryFlag ---


def test_injury_flag_create_valid():
    flag = InjuryFlagCreate(
        client_id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        body_part="left shoulder",
        pain_level=5,
        description="Dull ache during overhead press",
    )
    assert flag.pain_level == 5
    assert flag.body_part == "left shoulder"
    assert flag.session_entry_id is None


def test_injury_flag_create_requires_fields():
    with pytest.raises(ValidationError):
        InjuryFlagCreate()


def test_injury_flag_pain_level_too_low():
    with pytest.raises(ValidationError):
        InjuryFlagCreate(
            client_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            body_part="knee",
            pain_level=0,
        )


def test_injury_flag_pain_level_too_high():
    with pytest.raises(ValidationError):
        InjuryFlagCreate(
            client_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            body_part="knee",
            pain_level=11,
        )


def test_injury_flag_pain_level_valid_boundaries():
    low = InjuryFlagCreate(
        client_id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        body_part="knee",
        pain_level=1,
    )
    assert low.pain_level == 1

    high = InjuryFlagCreate(
        client_id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        body_part="knee",
        pain_level=10,
    )
    assert high.pain_level == 10


def test_injury_flag_create_rejects_empty_body_part():
    with pytest.raises(ValidationError):
        InjuryFlagCreate(
            client_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            body_part="",
            pain_level=5,
        )


def test_injury_flag_update_all_optional():
    u = InjuryFlagUpdate()
    assert u.body_part is None
    assert u.pain_level is None
    assert u.description is None
    assert u.resolved is None
    assert u.resolved_at is None


def test_injury_flag_update_pain_level_validation():
    with pytest.raises(ValidationError):
        InjuryFlagUpdate(pain_level=0)
    with pytest.raises(ValidationError):
        InjuryFlagUpdate(pain_level=11)

    valid = InjuryFlagUpdate(pain_level=5, resolved=True)
    assert valid.pain_level == 5
    assert valid.resolved is True


def test_injury_flag_update_rejects_resolved_at_without_resolved():
    with pytest.raises(ValidationError, match="resolved_at requires resolved=true"):
        InjuryFlagUpdate(resolved_at=datetime(2026, 3, 1, 10, 0, 0))


def test_injury_flag_update_rejects_resolved_at_with_resolved_false():
    with pytest.raises(ValidationError, match="resolved_at requires resolved=true"):
        InjuryFlagUpdate(resolved=False, resolved_at=datetime(2026, 3, 1, 10, 0, 0))


def test_injury_flag_update_allows_resolved_at_with_resolved_true():
    u = InjuryFlagUpdate(resolved=True, resolved_at=datetime(2026, 3, 1, 10, 0, 0))
    assert u.resolved is True
    assert u.resolved_at is not None


def test_injury_flag_update_rejects_empty_body_part():
    with pytest.raises(ValidationError):
        InjuryFlagUpdate(body_part="")


# --- ClientAnalysis ---


def test_client_analysis_response_from_attributes():
    obj = types.SimpleNamespace(
        id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        total_sessions=15,
        last_session_date=datetime(2026, 2, 19, 10, 0, 0),
        avg_weight_increase_pct_per_week=1.5,
        current_volume_trend="increasing",
        injury_risk_score=25.0,
        injury_risk_level=RiskLevelEnum.low,
        risk_factors=["tight hamstrings"],
        form_degradation_detected=False,
        overtraining_indicators=False,
        pain_pattern_detected=False,
        client_score=82.5,
        client_score_breakdown={"consistency": 90, "progression": 75},
        last_computed_at=datetime(2026, 2, 19, 12, 0, 0),
    )
    resp = ClientAnalysisResponse.model_validate(obj, from_attributes=True)
    assert resp.total_sessions == 15
    assert resp.injury_risk_level == RiskLevelEnum.low
    assert resp.client_score == 82.5


# --- Exercise ---


def test_exercise_create_requires_canonical_name():
    with pytest.raises(ValidationError):
        ExerciseCreate()


def test_exercise_create_valid():
    e = ExerciseCreate(
        canonical_name="Barbell Back Squat",
        aliases=["back squat", "squat"],
        category="compound",
        primary_muscles=["quadriceps", "glutes"],
        equipment=["barbell", "squat rack"],
        difficulty="intermediate",
    )
    assert e.canonical_name == "Barbell Back Squat"
    assert len(e.aliases) == 2
    assert e.common_errors is None


def test_exercise_create_rejects_empty_canonical_name():
    with pytest.raises(ValidationError):
        ExerciseCreate(canonical_name="")


# --- BrainConversation ---


def test_brain_conversation_create_valid_empty():
    c = BrainConversationCreate()
    assert c.title is None


def test_brain_conversation_create_with_title():
    c = BrainConversationCreate(title="Client progress review")
    assert c.title == "Client progress review"


def test_brain_conversation_update_rejects_empty_title():
    with pytest.raises(ValidationError):
        BrainConversationUpdate(title="")


# --- BrainMessage ---


def test_brain_message_create_requires_fields():
    with pytest.raises(ValidationError):
        BrainMessageCreate()


def test_brain_message_create_valid():
    m = BrainMessageCreate(role=MessageRoleEnum.user, content="How is Sarah progressing?")
    assert m.role == MessageRoleEnum.user
    assert m.content == "How is Sarah progressing?"


def test_brain_message_create_rejects_empty_content():
    with pytest.raises(ValidationError):
        BrainMessageCreate(role=MessageRoleEnum.user, content="")


def test_brain_message_create_invalid_role():
    with pytest.raises(ValidationError):
        BrainMessageCreate(role="system", content="Hello")


# --- Response from_attributes tests ---


def test_session_response_from_attributes():
    obj = types.SimpleNamespace(
        id=uuid.uuid4(),
        trainer_id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        started_at=datetime(2026, 2, 19, 10, 0, 0),
        ended_at=datetime(2026, 2, 19, 11, 0, 0),
        scheduled_for=None,
        duration_minutes=60,
        audio_url=None,
        audio_duration_seconds=None,
        raw_transcript="bench press 3 sets of 8",
        processing_status=ProcessingStatusEnum.completed,
        trainer_edited=False,
        plan_id=None,
        created_at=datetime(2026, 2, 19, 10, 0, 0),
        updated_at=datetime(2026, 2, 19, 11, 0, 0),
    )
    resp = SessionResponse.model_validate(obj, from_attributes=True)
    assert resp.duration_minutes == 60
    assert resp.processing_status == ProcessingStatusEnum.completed
    assert resp.scheduled_for is None
    assert resp.plan_id is None


def test_session_entry_response_from_attributes():
    obj = types.SimpleNamespace(
        id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        entry_type=EntryTypeEnum.exercise_card,
        sequence_order=1,
        exercise_name="Bench Press",
        exercise_canonical="barbell_bench_press",
        sets=[{"set": 1, "weight_kg": 80, "reps": 8}],
        total_volume_kg=640.0,
        form_notes=["Good form"],
        cues_given=["Elbows in"],
        cue_effectiveness={"Elbows in": "effective"},
        observation_text=None,
        attached_to_set=None,
        flag_color=None,
        flag_reason=None,
        performed_at=None,
        created_at=datetime(2026, 2, 19, 10, 5, 0),
    )
    resp = SessionEntryResponse.model_validate(obj, from_attributes=True)
    assert resp.entry_type == EntryTypeEnum.exercise_card
    assert resp.exercise_name == "Bench Press"
    assert resp.total_volume_kg == 640.0


def test_brain_message_response_from_attributes():
    obj = types.SimpleNamespace(
        id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        trainer_id=uuid.uuid4(),
        role=MessageRoleEnum.assistant,
        content="Sarah has improved her squat by 15% this month.",
        created_at=datetime(2026, 2, 19, 14, 30, 0),
    )
    resp = BrainMessageResponse.model_validate(obj, from_attributes=True)
    assert resp.role == MessageRoleEnum.assistant
    assert "Sarah" in resp.content
