import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

pytestmark = pytest.mark.asyncio(loop_scope="session")

from app.models import (
    BrainConversation,
    BrainMessage,
    Client,
    ClientAnalysis,
    EntryTypeEnum,
    Exercise,
    InjuryFlag,
    MessageRoleEnum,
    Session,
    SessionEntry,
    SessionPlan,
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


async def _create_session_entry(db_session, session_id, client_id, entry_type, sequence_order=1, **overrides):
    defaults = {
        "session_id": session_id,
        "client_id": client_id,
        "entry_type": entry_type,
        "sequence_order": sequence_order,
    }
    defaults.update(overrides)
    entry = SessionEntry(**defaults)
    db_session.add(entry)
    await db_session.flush()
    return entry


# --- 1. Trainer ---


async def test_create_trainer(db_session):
    trainer = await _create_trainer(db_session)
    result = await db_session.get(Trainer, trainer.id)
    assert result is not None
    assert result.email == trainer.email
    assert result.tier == TierEnum.free
    assert result.supabase_user_id is None


# --- 2. Trainer unique email ---


async def test_trainer_unique_email(db_session):
    email = f"dup-{uuid.uuid4().hex[:8]}@test.com"
    await _create_trainer(db_session, email=email)
    nested = await db_session.begin_nested()
    with pytest.raises(IntegrityError):
        await _create_trainer(db_session, email=email)
    await nested.rollback()


# --- 3. Client ---


async def test_create_client(db_session):
    trainer = await _create_trainer(db_session)
    client = await _create_client(db_session, trainer.id, goals=["strength", "mobility"])
    result = await db_session.get(Client, client.id)
    assert result is not None
    assert result.trainer_id == trainer.id
    assert result.goals == ["strength", "mobility"]
    assert result.archived is False


# --- 4. Client requires valid trainer ---


async def test_client_requires_valid_trainer(db_session):
    nested = await db_session.begin_nested()
    with pytest.raises(IntegrityError):
        await _create_client(db_session, uuid.uuid4())
    await nested.rollback()


# --- 5. Session with new fields ---


async def test_create_session_with_new_fields(db_session):
    trainer = await _create_trainer(db_session)
    client = await _create_client(db_session, trainer.id)
    scheduled = _utcnow()
    session = await _create_session(db_session, trainer.id, client.id, scheduled_for=scheduled)
    result = await db_session.get(Session, session.id)
    assert result is not None
    assert result.scheduled_for is not None
    assert result.plan_id is None
    assert result.transcript_embedding is None


# --- 6. Session requires valid client ---


async def test_session_requires_valid_client(db_session):
    trainer = await _create_trainer(db_session)
    nested = await db_session.begin_nested()
    with pytest.raises(IntegrityError):
        await _create_session(db_session, trainer.id, uuid.uuid4())
    await nested.rollback()


# --- 7. Exercise card entry ---


async def test_create_exercise_card_entry(db_session):
    trainer = await _create_trainer(db_session)
    client = await _create_client(db_session, trainer.id)
    session = await _create_session(db_session, trainer.id, client.id)

    sets_data = [
        {"set_number": 1, "weight_kg": 80, "reps": 8, "rpe": 7},
        {"set_number": 2, "weight_kg": 80, "reps": 7, "rpe": 8},
    ]
    entry = await _create_session_entry(
        db_session, session.id, client.id, EntryTypeEnum.exercise_card,
        exercise_name="Barbell Back Squat",
        exercise_canonical="barbell_back_squat",
        sets=sets_data,
        total_volume_kg=1200.0,
        form_notes=["depth good", "knees caving on set 2"],
        cues_given=["push knees out"],
    )
    result = await db_session.get(SessionEntry, entry.id)
    assert result is not None
    assert result.entry_type == EntryTypeEnum.exercise_card
    assert result.sets == sets_data
    assert result.form_notes == ["depth good", "knees caving on set 2"]
    assert result.observation_text is None


# --- 8. Observation card entry ---


async def test_create_observation_card_entry(db_session):
    trainer = await _create_trainer(db_session)
    client = await _create_client(db_session, trainer.id)
    session = await _create_session(db_session, trainer.id, client.id)

    entry = await _create_session_entry(
        db_session, session.id, client.id, EntryTypeEnum.observation_card,
        observation_text="Client seems fatigued today, lower energy than usual",
        flag_color="yellow",
        flag_reason="fatigue",
        attached_to_set=3,
    )
    result = await db_session.get(SessionEntry, entry.id)
    assert result is not None
    assert result.entry_type == EntryTypeEnum.observation_card
    assert result.observation_text == "Client seems fatigued today, lower energy than usual"
    assert result.flag_color == "yellow"
    assert result.attached_to_set == 3
    assert result.exercise_name is None


# --- 9. SessionEntry requires valid session ---


async def test_session_entry_requires_valid_session(db_session):
    trainer = await _create_trainer(db_session)
    client = await _create_client(db_session, trainer.id)
    nested = await db_session.begin_nested()
    with pytest.raises(IntegrityError):
        await _create_session_entry(
            db_session, uuid.uuid4(), client.id, EntryTypeEnum.exercise_card,
        )
    await nested.rollback()


# --- 10. SessionPlan ---


async def test_create_session_plan(db_session):
    trainer = await _create_trainer(db_session)
    client = await _create_client(db_session, trainer.id)

    plan = SessionPlan(
        client_id=client.id,
        trainer_id=trainer.id,
        plan_text="Focus on lower body: squats 5x5, RDLs 3x10, leg press 3x12",
        planned_for_date=date(2026, 2, 25),
    )
    db_session.add(plan)
    await db_session.flush()

    result = await db_session.get(SessionPlan, plan.id)
    assert result is not None
    assert result.plan_text.startswith("Focus on lower body")
    assert result.planned_for_date == date(2026, 2, 25)
    assert result.plan_text_embedding is None


# --- 11. Session linked to plan ---


async def test_session_linked_to_plan(db_session):
    trainer = await _create_trainer(db_session)
    client = await _create_client(db_session, trainer.id)
    plan = SessionPlan(
        client_id=client.id,
        trainer_id=trainer.id,
        plan_text="Upper body day: bench 5x5, rows 4x8",
    )
    db_session.add(plan)
    await db_session.flush()

    session = await _create_session(db_session, trainer.id, client.id, plan_id=plan.id)
    result = await db_session.get(Session, session.id)
    assert result.plan_id == plan.id


# --- 12. InjuryFlag with session_entry ---


async def test_create_injury_flag_with_session_entry(db_session):
    trainer = await _create_trainer(db_session)
    client = await _create_client(db_session, trainer.id)
    session = await _create_session(db_session, trainer.id, client.id)
    entry = await _create_session_entry(
        db_session, session.id, client.id, EntryTypeEnum.exercise_card,
        exercise_name="Squat",
    )

    flag = InjuryFlag(
        client_id=client.id,
        session_id=session.id,
        session_entry_id=entry.id,
        body_part="left knee",
        pain_level=6,
        description="Sharp pain during deep squat",
    )
    db_session.add(flag)
    await db_session.flush()

    result = await db_session.get(InjuryFlag, flag.id)
    assert result is not None
    assert result.session_entry_id == entry.id
    assert result.body_part == "left knee"
    assert result.resolved is False


# --- 13. InjuryFlag session_entry SET NULL on delete ---


async def test_injury_flag_session_entry_set_null_on_delete(db_session):
    trainer = await _create_trainer(db_session)
    client = await _create_client(db_session, trainer.id)
    session = await _create_session(db_session, trainer.id, client.id)
    entry = await _create_session_entry(
        db_session, session.id, client.id, EntryTypeEnum.exercise_card,
        exercise_name="Deadlift",
    )

    flag = InjuryFlag(
        client_id=client.id,
        session_id=session.id,
        session_entry_id=entry.id,
        body_part="lower back",
        pain_level=4,
    )
    db_session.add(flag)
    await db_session.flush()
    flag_id = flag.id

    # Delete the session entry — flag should survive with session_entry_id = NULL
    await db_session.delete(entry)
    await db_session.flush()

    # Expire and re-fetch to get fresh state from DB
    db_session.expire(flag)
    result = await db_session.get(InjuryFlag, flag_id)
    assert result is not None
    assert result.session_entry_id is None


# --- 14. ClientAnalysis with score ---


async def test_create_client_analysis_with_score(db_session):
    trainer = await _create_trainer(db_session)
    client = await _create_client(db_session, trainer.id)

    breakdown = {"consistency": 85, "progression": 70, "form": 90}
    analysis = ClientAnalysis(
        client_id=client.id,
        total_sessions=15,
        injury_risk_score=42.5,
        client_score=78.5,
        client_score_breakdown=breakdown,
    )
    db_session.add(analysis)
    await db_session.flush()

    result = await db_session.get(ClientAnalysis, analysis.id)
    assert result is not None
    assert result.client_score == 78.5
    assert result.client_score_breakdown == breakdown
    assert result.total_sessions == 15


# --- 15. BrainConversation + BrainMessage ---


async def test_create_brain_conversation_and_message(db_session):
    trainer = await _create_trainer(db_session)

    convo = BrainConversation(trainer_id=trainer.id, title="Client progress check")
    db_session.add(convo)
    await db_session.flush()

    msg1 = BrainMessage(
        conversation_id=convo.id,
        trainer_id=trainer.id,
        role=MessageRoleEnum.user,
        content="How is Sarah progressing on her squat?",
    )
    msg2 = BrainMessage(
        conversation_id=convo.id,
        trainer_id=trainer.id,
        role=MessageRoleEnum.assistant,
        content="Sarah has increased her squat by 10kg over the last 4 weeks.",
    )
    db_session.add_all([msg1, msg2])
    await db_session.flush()

    result = await db_session.get(BrainConversation, convo.id)
    assert result is not None
    assert result.title == "Client progress check"

    msgs = (await db_session.execute(
        select(BrainMessage).where(BrainMessage.conversation_id == convo.id).order_by(BrainMessage.created_at)
    )).scalars().all()
    assert len(msgs) == 2
    assert msgs[0].role == MessageRoleEnum.user
    assert msgs[1].role == MessageRoleEnum.assistant


# --- 16. Exercise unique canonical_name ---


async def test_exercise_unique_canonical_name(db_session):
    name = f"exercise_{uuid.uuid4().hex[:8]}"
    e1 = Exercise(canonical_name=name)
    db_session.add(e1)
    await db_session.flush()

    nested = await db_session.begin_nested()
    with pytest.raises(IntegrityError):
        e2 = Exercise(canonical_name=name)
        db_session.add(e2)
        await db_session.flush()
    await nested.rollback()


# --- 17. EntryType enum values ---


async def test_entry_type_enum_values(db_session):
    trainer = await _create_trainer(db_session)
    client = await _create_client(db_session, trainer.id)
    session = await _create_session(db_session, trainer.id, client.id)

    ex_entry = await _create_session_entry(
        db_session, session.id, client.id, EntryTypeEnum.exercise_card, sequence_order=1,
    )
    obs_entry = await _create_session_entry(
        db_session, session.id, client.id, EntryTypeEnum.observation_card, sequence_order=2,
    )

    assert (await db_session.get(SessionEntry, ex_entry.id)).entry_type == EntryTypeEnum.exercise_card
    assert (await db_session.get(SessionEntry, obs_entry.id)).entry_type == EntryTypeEnum.observation_card


# --- 18. Cascade delete trainer ---


async def test_cascade_delete_trainer(db_session):
    trainer = await _create_trainer(db_session)
    client = await _create_client(db_session, trainer.id)
    session = await _create_session(db_session, trainer.id, client.id)
    await _create_session_entry(
        db_session, session.id, client.id, EntryTypeEnum.exercise_card,
        exercise_name="Bench Press",
    )
    convo = BrainConversation(trainer_id=trainer.id, title="Test")
    db_session.add(convo)
    await db_session.flush()
    msg = BrainMessage(
        conversation_id=convo.id, trainer_id=trainer.id,
        role=MessageRoleEnum.user, content="test",
    )
    db_session.add(msg)
    await db_session.flush()

    client_id = client.id
    session_id = session.id
    convo_id = convo.id

    await db_session.delete(trainer)
    await db_session.flush()

    assert await db_session.get(Trainer, trainer.id) is None
    assert await db_session.get(Client, client_id) is None
    assert await db_session.get(Session, session_id) is None
    assert await db_session.get(BrainConversation, convo_id) is None

    # Verify deep cascades — entries and messages also gone
    entries = (await db_session.execute(
        select(SessionEntry).where(SessionEntry.session_id == session_id)
    )).scalars().all()
    assert entries == []

    msgs = (await db_session.execute(
        select(BrainMessage).where(BrainMessage.conversation_id == convo_id)
    )).scalars().all()
    assert msgs == []


# --- 19. Cascade delete session → entries + injury_flags ---


async def test_cascade_delete_session(db_session):
    trainer = await _create_trainer(db_session)
    client = await _create_client(db_session, trainer.id)
    session = await _create_session(db_session, trainer.id, client.id)
    entry = await _create_session_entry(
        db_session, session.id, client.id, EntryTypeEnum.exercise_card,
        exercise_name="Squat",
    )
    flag = InjuryFlag(
        client_id=client.id, session_id=session.id,
        body_part="knee", pain_level=5,
    )
    db_session.add(flag)
    await db_session.flush()
    entry_id = entry.id
    flag_id = flag.id

    await db_session.delete(session)
    await db_session.flush()

    assert await db_session.get(Session, session.id) is None
    assert await db_session.get(SessionEntry, entry_id) is None
    assert await db_session.get(InjuryFlag, flag_id) is None
    # Client and trainer survive
    assert await db_session.get(Client, client.id) is not None
    assert await db_session.get(Trainer, trainer.id) is not None


# --- 20. Cascade delete client → sessions, entries, plans, flags, analysis ---


async def test_cascade_delete_client(db_session):
    trainer = await _create_trainer(db_session)
    client = await _create_client(db_session, trainer.id)
    session = await _create_session(db_session, trainer.id, client.id)
    entry = await _create_session_entry(
        db_session, session.id, client.id, EntryTypeEnum.exercise_card,
        exercise_name="Bench",
    )
    plan = SessionPlan(
        client_id=client.id, trainer_id=trainer.id,
        plan_text="Test plan",
    )
    db_session.add(plan)
    await db_session.flush()
    flag = InjuryFlag(
        client_id=client.id, session_id=session.id,
        body_part="shoulder", pain_level=3,
    )
    analysis = ClientAnalysis(client_id=client.id, total_sessions=5)
    db_session.add_all([flag, analysis])
    await db_session.flush()

    ids = {
        "client": client.id, "session": session.id, "entry": entry.id,
        "plan": plan.id, "flag": flag.id, "analysis": analysis.id,
    }

    await db_session.delete(client)
    await db_session.flush()

    assert await db_session.get(Client, ids["client"]) is None
    assert await db_session.get(Session, ids["session"]) is None
    assert await db_session.get(SessionEntry, ids["entry"]) is None
    assert await db_session.get(SessionPlan, ids["plan"]) is None
    assert await db_session.get(InjuryFlag, ids["flag"]) is None
    assert await db_session.get(ClientAnalysis, ids["analysis"]) is None
    # Trainer survives
    assert await db_session.get(Trainer, trainer.id) is not None


# --- 21. SessionPlan delete → sessions.plan_id SET NULL ---


async def test_session_plan_set_null_on_delete(db_session):
    trainer = await _create_trainer(db_session)
    client = await _create_client(db_session, trainer.id)
    plan = SessionPlan(
        client_id=client.id, trainer_id=trainer.id,
        plan_text="Leg day plan",
    )
    db_session.add(plan)
    await db_session.flush()

    session = await _create_session(db_session, trainer.id, client.id, plan_id=plan.id)
    session_id = session.id
    assert session.plan_id == plan.id

    await db_session.delete(plan)
    await db_session.flush()

    db_session.expire(session)
    result = await db_session.get(Session, session_id)
    assert result is not None
    assert result.plan_id is None


# --- 22. BrainConversation delete → messages CASCADE ---


async def test_cascade_delete_brain_conversation(db_session):
    trainer = await _create_trainer(db_session)
    convo = BrainConversation(trainer_id=trainer.id, title="Test convo")
    db_session.add(convo)
    await db_session.flush()

    msg = BrainMessage(
        conversation_id=convo.id, trainer_id=trainer.id,
        role=MessageRoleEnum.user, content="Hello",
    )
    db_session.add(msg)
    await db_session.flush()
    msg_id = msg.id

    await db_session.delete(convo)
    await db_session.flush()

    assert await db_session.get(BrainConversation, convo.id) is None
    assert await db_session.get(BrainMessage, msg_id) is None
    # Trainer survives
    assert await db_session.get(Trainer, trainer.id) is not None
