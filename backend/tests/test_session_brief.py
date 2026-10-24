"""Tests for pre-session briefs: the facts worked out in code, and POST /sessions/{id}/brief.

Claude is mocked; what's tested is what it's given, and when it's called at all.
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import httpx
import pytest

from app.models import Client, Session, SessionEntry, Trainer

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _claude_returning(text: str) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    mock = AsyncMock()
    mock.messages.create = AsyncMock(return_value=response)
    return mock


def _patch_claude(mock: MagicMock):
    return patch("app.services.session_brief.anthropic.AsyncAnthropic", return_value=mock)


async def _session(db, trainer, client, *, days_ago, ended=True, entries=()):
    started = datetime.now(timezone.utc) - timedelta(days=days_ago, hours=1)
    session = Session(
        trainer_id=trainer.id, client_id=client.id, started_at=started,
        ended_at=started + timedelta(minutes=50) if ended else None,
    )
    db.add(session)
    await db.flush()
    for i, fields in enumerate(entries, start=1):
        db.add(SessionEntry(session_id=session.id, client_id=client.id, sequence_order=i, **fields))
    await db.flush()
    return session


def _lift(canonical: str, kg: float, notes: str | None = None) -> dict:
    sets = [{"reps": 10, "weight": kg, "weight_unit": "kg"}]
    if notes:
        sets[0]["notes"] = notes
    return {"entry_type": "exercise_card", "exercise_name": canonical, "exercise_canonical": canonical, "sets": sets}


def _note(text: str, flag: str | None = None) -> dict:
    return {"entry_type": "observation_card", "observation_text": text, "flag_color": flag}


async def _brief_prompt(client, session) -> str:
    claude = _claude_returning("- A note.")
    with _patch_claude(claude):
        response = await client.post(f"/api/v1/sessions/{session.id}/brief")
    assert response.status_code == 200
    return claude.messages.create.await_args.kwargs["messages"][0]["content"]


# --- Facts worked out in code ---


async def test_prompt_has_weight_changes_pain_and_gaps(client, trainer_and_client, db_session):
    trainer, db_client = trainer_and_client
    await _session(db_session, trainer, db_client, days_ago=20, entries=[_lift("Lat Pulldown", 50)])
    await _session(db_session, trainer, db_client, days_ago=6, entries=[
        _lift("Lat Pulldown", 40, notes="left shoulder pain on the last reps"),
        _note("Shoulder sore again", flag="yellow"),
        _note("Chatty today"),
    ])
    upcoming = await _session(db_session, trainer, db_client, days_ago=0, ended=False)

    prompt = await _brief_prompt(client, upcoming)

    assert "Lat Pulldown: heaviest set 50kg 20 days ago, 40kg 6 days ago (-20%, 2 sessions)" in prompt
    assert "6 days ago, during Lat Pulldown: left shoulder pain on the last reps" in prompt
    assert "6 days ago: Shoulder sore again" in prompt
    assert "Chatty today" not in prompt.split("Pain and flags")[1]
    assert "Not trained in the last four weeks: hamstrings, quads, glutes, calves" in prompt
    assert "Sessions in the last four weeks: 2" in prompt


async def test_unrecognised_exercise_makes_gaps_unknown(client, trainer_and_client, db_session):
    """An exercise whose muscles are unknown could be training any group, so no gap is claimed."""
    trainer, db_client = trainer_and_client
    await _session(db_session, trainer, db_client, days_ago=3, entries=[_lift("Zorbnik Twist", 10)])
    upcoming = await _session(db_session, trainer, db_client, days_ago=0, ended=False)

    prompt = await _brief_prompt(client, upcoming)
    assert "Not trained in the last four weeks: unknown (unrecognised exercises: Zorbnik Twist)" in prompt


async def test_single_sessions_and_bodyweight_lifts_have_no_weight_change(client, trainer_and_client, db_session):
    trainer, db_client = trainer_and_client
    await _session(db_session, trainer, db_client, days_ago=9, entries=[_lift("Push-Up", 0), _lift("Lat Pulldown", 50)])
    await _session(db_session, trainer, db_client, days_ago=2, entries=[_lift("Push-Up", 0)])
    upcoming = await _session(db_session, trainer, db_client, days_ago=0, ended=False)

    prompt = await _brief_prompt(client, upcoming)
    assert "- none: no lift was done twice with weight" in prompt


async def test_only_finished_sessions_from_the_last_four_weeks_count(client, trainer_and_client, db_session):
    trainer, db_client = trainer_and_client
    await _session(db_session, trainer, db_client, days_ago=40, entries=[_lift("Lat Pulldown", 90)])
    await _session(db_session, trainer, db_client, days_ago=5, entries=[_lift("Lat Pulldown", 50)])
    await _session(db_session, trainer, db_client, days_ago=1, ended=False, entries=[_lift("Lat Pulldown", 70)])
    upcoming = await _session(db_session, trainer, db_client, days_ago=0, ended=False)

    prompt = await _brief_prompt(client, upcoming)
    assert "Sessions in the last four weeks: 1" in prompt
    assert "90kg" not in prompt and "70kg" not in prompt


# --- Endpoint ---


async def test_brief_is_returned(client, trainer_and_client, db_session):
    trainer, db_client = trainer_and_client
    await _session(db_session, trainer, db_client, days_ago=3, entries=[_lift("Lat Pulldown", 50)])
    upcoming = await _session(db_session, trainer, db_client, days_ago=0, ended=False)
    with _patch_claude(_claude_returning("- Lat pulldown at 50kg last time.")):
        response = await client.post(f"/api/v1/sessions/{upcoming.id}/brief")
    assert response.json()["data"] == {"ai_brief": "- Lat pulldown at 50kg last time."}


async def test_no_history_means_no_brief_and_no_claude_call(client, trainer_and_client, db_session):
    trainer, db_client = trainer_and_client
    upcoming = await _session(db_session, trainer, db_client, days_ago=0, ended=False)
    claude = _claude_returning("unused")
    with _patch_claude(claude):
        response = await client.post(f"/api/v1/sessions/{upcoming.id}/brief")
    assert response.status_code == 200
    assert response.json()["data"]["ai_brief"] is None
    claude.messages.create.assert_not_awaited()


async def test_ended_session_is_409(client, trainer_and_client, db_session):
    trainer, db_client = trainer_and_client
    done = await _session(db_session, trainer, db_client, days_ago=1)
    response = await client.post(f"/api/v1/sessions/{done.id}/brief")
    assert response.status_code == 409


async def test_claude_failure_is_502(client, trainer_and_client, db_session):
    trainer, db_client = trainer_and_client
    await _session(db_session, trainer, db_client, days_ago=3, entries=[_lift("Lat Pulldown", 50)])
    upcoming = await _session(db_session, trainer, db_client, days_ago=0, ended=False)
    claude = AsyncMock()
    claude.messages.create = AsyncMock(
        side_effect=anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com"))
    )
    with _patch_claude(claude):
        response = await client.post(f"/api/v1/sessions/{upcoming.id}/brief")
    assert response.status_code == 502


async def test_other_trainers_session_is_404(client, trainer_and_client, db_session):
    other_trainer = Trainer(email=f"other-brief-{uuid.uuid4().hex[:8]}@test.com", name="Other")
    db_session.add(other_trainer)
    await db_session.flush()
    other_client = Client(trainer_id=other_trainer.id, name="Other Client")
    db_session.add(other_client)
    await db_session.flush()
    session = await _session(db_session, other_trainer, other_client, days_ago=0, ended=False)
    response = await client.post(f"/api/v1/sessions/{session.id}/brief")
    assert response.status_code == 404
