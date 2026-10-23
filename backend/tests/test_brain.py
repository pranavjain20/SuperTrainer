"""Tests for the Brain: its context and POST /brain/ask. Claude is mocked."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import httpx
import pytest

from app.models import Client, Session, SessionEntry, Trainer
from app.services.brain import build_brain_context

pytestmark = pytest.mark.asyncio(loop_scope="session")

NOW = datetime(2026, 3, 10, 18, 0, 0, tzinfo=timezone.utc)


def _claude_returning(text: str) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    mock = AsyncMock()
    mock.messages.create = AsyncMock(return_value=response)
    return mock


async def _add_session(db, trainer, client, days_ago, *, ended=True, entries=()):
    started = NOW - timedelta(days=days_ago, hours=2)
    session = Session(
        trainer_id=trainer.id, client_id=client.id, started_at=started,
        ended_at=started + timedelta(minutes=45) if ended else None,
        duration_minutes=45 if ended else None,
    )
    db.add(session)
    await db.flush()
    for i, fields in enumerate(entries, start=1):
        db.add(SessionEntry(session_id=session.id, client_id=client.id, sequence_order=i, **fields))
    await db.flush()
    return session


BENCH = {
    "entry_type": "exercise_card", "exercise_name": "bench", "exercise_canonical": "Barbell Bench Press",
    "sets": [{"reps": 5, "weight": 80, "weight_unit": "kg"}],
}


async def test_context_lists_each_client_with_relative_days(trainer_and_client, db_session):
    trainer, db_client = trainer_and_client
    await _add_session(db_session, trainer, db_client, 3, entries=[BENCH])
    await _add_session(db_session, trainer, db_client, 0, ended=False)

    context = await build_brain_context(db_session, trainer.id, NOW)

    assert f"## {db_client.name}" in context
    assert "Session 3 days ago, 45 min:" in context
    assert "  - Barbell Bench Press: 1 set of 5 reps at 80kg" in context
    assert "Session today (in progress):" in context
    assert "2026-" not in context  # no calendar dates, only relative days


async def test_context_says_yesterday(trainer_and_client, db_session):
    trainer, db_client = trainer_and_client
    await _add_session(db_session, trainer, db_client, 1)
    assert "Session yesterday" in await build_brain_context(db_session, trainer.id, NOW)


async def test_context_leaves_out_archived_clients_and_other_trainers(trainer_and_client, db_session):
    trainer, db_client = trainer_and_client
    db_session.add(Client(trainer_id=trainer.id, name="Archived Annie", archived=True))
    other_trainer = Trainer(email=f"other-brain-{uuid.uuid4().hex[:8]}@test.com", name="Other")
    db_session.add(other_trainer)
    await db_session.flush()
    stranger = Client(trainer_id=other_trainer.id, name="Someone Else")
    db_session.add(stranger)
    await db_session.flush()
    await _add_session(db_session, other_trainer, stranger, 2, entries=[BENCH])

    context = await build_brain_context(db_session, trainer.id, NOW)
    assert db_client.name in context
    assert "Archived Annie" not in context
    assert "Someone Else" not in context


async def test_ask_sends_the_question_with_the_context(client, trainer_and_client, db_session):
    trainer, db_client = trainer_and_client
    await _add_session(db_session, trainer, db_client, 3, entries=[BENCH])
    claude = _claude_returning("Bench is at 80kg for 5.")

    with patch("app.services.brain.anthropic.AsyncAnthropic", return_value=claude):
        response = await client.post("/api/v1/brain/ask", json={"question": "How is bench going?"})

    assert response.status_code == 200
    assert response.json()["data"] == {"answer": "Bench is at 80kg for 5."}
    kwargs = claude.messages.create.await_args.kwargs
    assert kwargs["messages"] == [{"role": "user", "content": "How is bench going?"}]
    assert "Barbell Bench Press: 1 set of 5 reps at 80kg" in kwargs["system"]


async def test_ask_rejects_empty_and_overlong_questions(client, trainer_and_client):
    assert (await client.post("/api/v1/brain/ask", json={"question": ""})).status_code == 422
    assert (await client.post("/api/v1/brain/ask", json={"question": "x" * 501})).status_code == 422


async def test_ask_turns_a_claude_failure_into_502(client, trainer_and_client):
    claude = AsyncMock()
    claude.messages.create = AsyncMock(
        side_effect=anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com"))
    )
    with patch("app.services.brain.anthropic.AsyncAnthropic", return_value=claude):
        response = await client.post("/api/v1/brain/ask", json={"question": "Anything?"})
    assert response.status_code == 502


async def test_context_opens_with_every_clients_injury_history(trainer_and_client, db_session):
    """A roster-wide question ("who has an injury?") must see every client, even one without sessions."""
    trainer, db_client = trainer_and_client
    db_session.add(Client(trainer_id=trainer.id, name="Quiet Quinn", injury_history="Mild lower back pain"))
    await db_session.flush()
    context = await build_brain_context(db_session, trainer.id, NOW)
    roster = context.split("\n\n")[0]
    assert roster.startswith("## Roster")
    assert "- Quiet Quinn: goals not recorded; injury history: Mild lower back pain" in roster
    assert f"- {db_client.name}:" in roster
