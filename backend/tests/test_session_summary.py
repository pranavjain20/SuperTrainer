"""Tests for session summaries: the service, the prompt, and POST /sessions/{id}/summary.

Claude is mocked; what's tested is when it's called, what it's given, and how
the result is stored and cleared.
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import httpx
import pytest

from app.models import Client, Session, SessionEntry, Trainer

pytestmark = pytest.mark.asyncio(loop_scope="session")

T0 = datetime(2026, 3, 2, 10, 0, 0, tzinfo=timezone.utc)


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
    return patch("app.services.session_summary.anthropic.AsyncAnthropic", return_value=mock)


async def _session(db, trainer, client, *, ended=True, started_at=T0, entries=()):
    session = Session(
        trainer_id=trainer.id, client_id=client.id, started_at=started_at,
        ended_at=started_at + timedelta(minutes=50) if ended else None,
        duration_minutes=50 if ended else None,
    )
    db.add(session)
    await db.flush()
    for i, fields in enumerate(entries, start=1):
        db.add(SessionEntry(session_id=session.id, client_id=client.id, sequence_order=i, **fields))
    await db.flush()
    return session


SQUATS = {
    "entry_type": "exercise_card", "exercise_name": "Goblet squats", "exercise_canonical": "Goblet Squat",
    "sets": [{"reps": 10, "weight": 16, "weight_unit": "kg"}, {"reps": 10, "weight": 20, "weight_unit": "kg", "rpe": 8}],
}
KNEE_NOTE = {"entry_type": "observation_card", "observation_text": "Knees caved in on the last squat set."}


# --- Endpoint ---


async def test_summary_written_once_and_stored(client, trainer_and_client, db_session):
    trainer, db_client = trainer_and_client
    session = await _session(db_session, trainer, db_client, entries=[SQUATS])
    claude = _claude_returning("Goblet squats 2 sets, up to 20kg at RPE 8.")

    with _patch_claude(claude):
        first = await client.post(f"/api/v1/sessions/{session.id}/summary")
        second = await client.post(f"/api/v1/sessions/{session.id}/summary")

    assert first.status_code == 200
    assert first.json()["data"]["ai_summary"] == "Goblet squats 2 sets, up to 20kg at RPE 8."
    assert second.json() == first.json()
    assert claude.messages.create.await_count == 1

    got = await client.get(f"/api/v1/sessions/{session.id}")
    assert got.json()["data"]["ai_summary"] == "Goblet squats 2 sets, up to 20kg at RPE 8."


async def test_summary_needs_an_ended_session(client, trainer_and_client, db_session):
    trainer, db_client = trainer_and_client
    session = await _session(db_session, trainer, db_client, ended=False, entries=[SQUATS])
    claude = _claude_returning("unused")
    with _patch_claude(claude):
        response = await client.post(f"/api/v1/sessions/{session.id}/summary")
    assert response.status_code == 409
    claude.messages.create.assert_not_awaited()


async def test_empty_session_has_no_summary_and_no_claude_call(client, trainer_and_client, db_session):
    trainer, db_client = trainer_and_client
    session = await _session(db_session, trainer, db_client)
    claude = _claude_returning("unused")
    with _patch_claude(claude):
        response = await client.post(f"/api/v1/sessions/{session.id}/summary")
    assert response.status_code == 200
    assert response.json()["data"]["ai_summary"] is None
    claude.messages.create.assert_not_awaited()


async def test_claude_failure_is_a_502_and_stores_nothing(client, trainer_and_client, db_session):
    trainer, db_client = trainer_and_client
    session = await _session(db_session, trainer, db_client, entries=[SQUATS])
    claude = AsyncMock()
    claude.messages.create = AsyncMock(
        side_effect=anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com"))
    )
    with _patch_claude(claude):
        response = await client.post(f"/api/v1/sessions/{session.id}/summary")
    assert response.status_code == 502
    await db_session.refresh(session)
    assert session.ai_summary is None


async def test_other_trainers_session_is_404(client, trainer_and_client, db_session):
    other_trainer = Trainer(email=f"other-sum-{uuid.uuid4().hex[:8]}@test.com", name="Other")
    db_session.add(other_trainer)
    await db_session.flush()
    other_client = Client(trainer_id=other_trainer.id, name="Other Client")
    db_session.add(other_client)
    await db_session.flush()
    session = await _session(db_session, other_trainer, other_client, entries=[SQUATS])
    response = await client.post(f"/api/v1/sessions/{session.id}/summary")
    assert response.status_code == 404


async def test_missing_session_is_404(client, trainer_and_client):
    response = await client.post(f"/api/v1/sessions/{uuid.uuid4()}/summary")
    assert response.status_code == 404


async def _summarized(client, db_session, trainer, db_client):
    session = await _session(db_session, trainer, db_client, entries=[SQUATS])
    with _patch_claude(_claude_returning("A recap.")):
        await client.post(f"/api/v1/sessions/{session.id}/summary")
    return session


async def _summary_of(client, session) -> str | None:
    return (await client.get(f"/api/v1/sessions/{session.id}")).json()["data"]["ai_summary"]


async def test_editing_an_entry_clears_the_summary(client, trainer_and_client, db_session):
    trainer, db_client = trainer_and_client
    session = await _summarized(client, db_session, trainer, db_client)
    entries = (await client.get(f"/api/v1/sessions/{session.id}/entries")).json()["data"]
    await client.patch(f"/api/v1/entries/{entries[0]['id']}", json={"exercise_name": "Front squats"})
    assert await _summary_of(client, session) is None


async def test_adding_an_entry_clears_the_summary(client, trainer_and_client, db_session):
    trainer, db_client = trainer_and_client
    session = await _summarized(client, db_session, trainer, db_client)
    await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json={"entry_type": "observation_card", "observation_text": "Left early"},
    )
    assert await _summary_of(client, session) is None


async def test_deleting_an_entry_clears_the_summary(client, trainer_and_client, db_session):
    trainer, db_client = trainer_and_client
    session = await _summarized(client, db_session, trainer, db_client)
    entries = (await client.get(f"/api/v1/sessions/{session.id}/entries")).json()["data"]
    await client.delete(f"/api/v1/entries/{entries[0]['id']}")
    assert await _summary_of(client, session) is None


async def test_editing_another_session_keeps_this_summary(client, trainer_and_client, db_session):
    trainer, db_client = trainer_and_client
    kept = await _summarized(client, db_session, trainer, db_client)
    other = await _session(db_session, trainer, db_client, started_at=T0 + timedelta(days=1), entries=[SQUATS])
    entries = (await client.get(f"/api/v1/sessions/{other.id}/entries")).json()["data"]
    await client.patch(f"/api/v1/entries/{entries[0]['id']}", json={"exercise_name": "Front squats"})
    assert await _summary_of(client, kept) == "A recap."


async def test_prompt_carries_the_session_and_previous_best(client, trainer_and_client, db_session):
    trainer, db_client = trainer_and_client
    # Older sets store weight_kg; the previous best must still count them
    earlier = {**SQUATS, "sets": [{"reps": 8, "weight_kg": 18}, {"reps": 8, "weight": 17, "weight_unit": "kg"}]}
    await _session(db_session, trainer, db_client, started_at=T0 - timedelta(days=7), entries=[earlier])
    session = await _session(db_session, trainer, db_client, entries=[SQUATS, KNEE_NOTE])
    claude = _claude_returning("A recap.")
    with _patch_claude(claude):
        await client.post(f"/api/v1/sessions/{session.id}/summary")

    prompt = claude.messages.create.await_args.kwargs["messages"][0]["content"]
    assert db_client.name in prompt
    assert "Goblet Squat: 1 set of 10 reps at 16kg; 1 set of 10 reps at 20kg, RPE 8 [previous best: 18]" in prompt
    assert "Note: Knees caved in on the last squat set." in prompt
