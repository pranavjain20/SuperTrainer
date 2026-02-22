"""Cross-endpoint integration tests.

Tests that span multiple endpoints: cascades visible through the API,
cross-entity validation, and behavior after state mutations.
"""

import uuid
from datetime import datetime, timezone

import pytest

from app.models import Client, Session, SessionPlan

pytestmark = pytest.mark.asyncio(loop_scope="session")


# --- Helpers ---


def _exercise_card(**overrides):
    base = {"entry_type": "exercise_card", "exercise_name": "Bench Press"}
    base.update(overrides)
    return base


def _flag(client_id, session_id, **overrides):
    base = {
        "client_id": str(client_id),
        "session_id": str(session_id),
        "body_part": "left knee",
        "pain_level": 5,
    }
    base.update(overrides)
    return base


# --- Entry delete → injury flag SET NULL ---


async def test_entry_delete_nullifies_injury_flag_session_entry_id(
    client, trainer_client_session, db_session,
):
    """Deleting a session entry should SET NULL on related injury flags, not delete them."""
    _, db_client, session = trainer_client_session

    # Create an entry
    entry_resp = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json=_exercise_card(exercise_name="Squat"),
    )
    entry_id = entry_resp.json()["data"]["id"]

    # Create an injury flag linked to that entry
    flag_resp = await client.post(
        "/api/v1/injury-flags",
        json=_flag(
            db_client.id, session.id,
            session_entry_id=entry_id,
            body_part="knee",
        ),
    )
    flag_id = flag_resp.json()["data"]["id"]

    # Delete the entry
    delete_resp = await client.delete(f"/api/v1/entries/{entry_id}")
    assert delete_resp.status_code == 204

    # Flag should survive with session_entry_id = null
    flag_get = await client.get(f"/api/v1/injury-flags/{flag_id}")
    assert flag_get.status_code == 200
    assert flag_get.json()["data"]["session_entry_id"] is None
    assert flag_get.json()["data"]["body_part"] == "knee"


# --- Archived client child entity access ---


async def test_archived_client_sessions_still_accessible(
    client, trainer_client_session, db_session,
):
    """Archiving a client should not block access to their sessions via direct GET."""
    trainer, _, _ = trainer_client_session

    # Create a client, session, then archive the client
    create_resp = await client.post("/api/v1/clients", json={"name": "Archive Test"})
    client_id = create_resp.json()["data"]["id"]

    session_resp = await client.post("/api/v1/sessions", json={
        "client_id": client_id,
        "started_at": "2026-02-22T10:00:00Z",
    })
    session_id = session_resp.json()["data"]["id"]

    # Archive the client
    await client.patch(f"/api/v1/clients/{client_id}/archive")

    # Session should still be accessible via direct GET
    get_resp = await client.get(f"/api/v1/sessions/{session_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["client_id"] == client_id


async def test_archived_client_entries_still_accessible(
    client, trainer_client_session, db_session,
):
    """Archiving a client should not block access to their entries via direct GET."""
    trainer, _, _ = trainer_client_session

    create_resp = await client.post("/api/v1/clients", json={"name": "Archive Entry Test"})
    client_id = create_resp.json()["data"]["id"]

    session_resp = await client.post("/api/v1/sessions", json={
        "client_id": client_id,
        "started_at": "2026-02-22T11:00:00Z",
    })
    session_id = session_resp.json()["data"]["id"]

    entry_resp = await client.post(
        f"/api/v1/sessions/{session_id}/entries",
        json=_exercise_card(exercise_name="Deadlift"),
    )
    entry_id = entry_resp.json()["data"]["id"]

    await client.patch(f"/api/v1/clients/{client_id}/archive")

    get_resp = await client.get(f"/api/v1/entries/{entry_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["exercise_name"] == "Deadlift"


async def test_archived_client_plans_still_accessible(
    client, trainer_client_session, db_session,
):
    """Archiving a client should not block access to their plans via direct GET."""
    trainer, _, _ = trainer_client_session

    create_resp = await client.post("/api/v1/clients", json={"name": "Archive Plan Test"})
    client_id = create_resp.json()["data"]["id"]

    plan_resp = await client.post("/api/v1/plans", json={
        "client_id": client_id,
        "plan_text": "Test plan for archive",
    })
    plan_id = plan_resp.json()["data"]["id"]

    await client.patch(f"/api/v1/clients/{client_id}/archive")

    get_resp = await client.get(f"/api/v1/plans/{plan_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["plan_text"] == "Test plan for archive"


async def test_archived_client_injury_flags_still_accessible(
    client, trainer_client_session, db_session,
):
    """Archiving a client should not block access to their injury flags via direct GET."""
    trainer, _, _ = trainer_client_session

    create_resp = await client.post("/api/v1/clients", json={"name": "Archive Flag Test"})
    client_id = create_resp.json()["data"]["id"]

    session_resp = await client.post("/api/v1/sessions", json={
        "client_id": client_id,
        "started_at": "2026-02-22T12:00:00Z",
    })
    session_id = session_resp.json()["data"]["id"]

    flag_resp = await client.post("/api/v1/injury-flags", json=_flag(
        client_id, session_id, body_part="archived knee",
    ))
    flag_id = flag_resp.json()["data"]["id"]

    await client.patch(f"/api/v1/clients/{client_id}/archive")

    get_resp = await client.get(f"/api/v1/injury-flags/{flag_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["body_part"] == "archived knee"


# --- Sequence order after deletion ---


async def test_sequence_order_after_entry_deletion_no_collision(
    client, trainer_client_session, db_session,
):
    """Delete entry #1, create new → should use max+1 (no collision with #2)."""
    trainer, db_client, _ = trainer_client_session
    fresh_session = Session(
        trainer_id=trainer.id,
        client_id=db_client.id,
        started_at=datetime(2026, 2, 23, 15, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(fresh_session)
    await db_session.flush()

    # Create entries 1, 2
    resp1 = await client.post(
        f"/api/v1/sessions/{fresh_session.id}/entries",
        json=_exercise_card(exercise_name="First"),
    )
    resp2 = await client.post(
        f"/api/v1/sessions/{fresh_session.id}/entries",
        json=_exercise_card(exercise_name="Second"),
    )
    entry1_id = resp1.json()["data"]["id"]
    assert resp1.json()["data"]["sequence_order"] == 1
    assert resp2.json()["data"]["sequence_order"] == 2

    # Delete entry #1
    await client.delete(f"/api/v1/entries/{entry1_id}")

    # Create a new entry — should get sequence_order=3 (max+1), not 1
    resp3 = await client.post(
        f"/api/v1/sessions/{fresh_session.id}/entries",
        json=_exercise_card(exercise_name="Third"),
    )
    assert resp3.status_code == 201
    assert resp3.json()["data"]["sequence_order"] == 3


# --- Plan-client mismatch ---


async def test_session_create_plan_client_mismatch_422(
    client, trainer_client_session, db_session,
):
    """Creating a session with a plan belonging to a different client should 422."""
    trainer, db_client, _ = trainer_client_session

    # Create a second client (same trainer)
    other_client = Client(trainer_id=trainer.id, name="Other Plan Client")
    db_session.add(other_client)
    await db_session.flush()

    # Create a plan for the other client
    plan = SessionPlan(
        client_id=other_client.id,
        trainer_id=trainer.id,
        plan_text="This plan belongs to other_client",
    )
    db_session.add(plan)
    await db_session.flush()

    # Try to create session for db_client with other_client's plan
    response = await client.post("/api/v1/sessions", json={
        "client_id": str(db_client.id),
        "started_at": "2026-02-22T14:00:00Z",
        "plan_id": str(plan.id),
    })
    assert response.status_code == 422
    assert "Plan does not belong to this client" in response.json()["error"]["message"]


# --- Non-existent session_entry_id on injury flag create ---


async def test_injury_flag_create_nonexistent_session_entry_id_404(
    client, trainer_client_session,
):
    """Creating an injury flag with a non-existent session_entry_id should 404."""
    _, db_client, session = trainer_client_session

    response = await client.post("/api/v1/injury-flags", json=_flag(
        db_client.id, session.id,
        session_entry_id=str(uuid.uuid4()),
    ))
    assert response.status_code == 404
    assert "Session entry not found" in response.json()["error"]["message"]


# --- Delete plan doesn't affect siblings ---


async def test_delete_plan_does_not_affect_sibling_plans(
    client, trainer_client_session,
):
    """Deleting one plan should not affect other plans for the same client."""
    _, db_client, _ = trainer_client_session

    # Create two plans for the same client
    resp_a = await client.post("/api/v1/plans", json={
        "client_id": str(db_client.id),
        "plan_text": "Plan A - keep",
    })
    resp_b = await client.post("/api/v1/plans", json={
        "client_id": str(db_client.id),
        "plan_text": "Plan B - delete",
    })
    plan_a_id = resp_a.json()["data"]["id"]
    plan_b_id = resp_b.json()["data"]["id"]

    # Delete plan B
    delete_resp = await client.delete(f"/api/v1/plans/{plan_b_id}")
    assert delete_resp.status_code == 204

    # Plan A should still exist and be intact
    get_resp = await client.get(f"/api/v1/plans/{plan_a_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["plan_text"] == "Plan A - keep"

    # Plan B should be gone
    get_resp_b = await client.get(f"/api/v1/plans/{plan_b_id}")
    assert get_resp_b.status_code == 404


# --- Trainer cascade deletes sessions and brain messages ---


async def test_trainer_cascade_deletes_sessions(db_session):
    """Deleting a trainer should cascade-delete their sessions (FK fix from Day 8)."""
    from app.models import Trainer

    trainer = Trainer(email=f"cascade-{uuid.uuid4().hex[:8]}@test.com", name="Cascade Test")
    db_session.add(trainer)
    await db_session.flush()

    client_obj = Client(trainer_id=trainer.id, name="Cascade Client")
    db_session.add(client_obj)
    await db_session.flush()

    session_obj = Session(
        trainer_id=trainer.id,
        client_id=client_obj.id,
        started_at=datetime(2026, 2, 22, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(session_obj)
    await db_session.flush()
    session_id = session_obj.id

    # Delete trainer — should cascade to clients → sessions
    await db_session.delete(trainer)
    await db_session.commit()

    # Session should be gone
    result = await db_session.get(Session, session_id)
    assert result is None


# --- Session entry belongs to wrong session on injury flag create ---


async def test_injury_flag_create_entry_wrong_session_422(
    client, trainer_client_session, db_session,
):
    """Creating an injury flag with a session_entry_id from a different session should 422."""
    trainer, db_client, session = trainer_client_session

    # Create a second session
    other_session = Session(
        trainer_id=trainer.id,
        client_id=db_client.id,
        started_at=datetime(2026, 2, 22, 15, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(other_session)
    await db_session.flush()

    # Create an entry in the OTHER session
    entry_resp = await client.post(
        f"/api/v1/sessions/{other_session.id}/entries",
        json=_exercise_card(exercise_name="Deadlift"),
    )
    entry_id = entry_resp.json()["data"]["id"]

    # Try to create injury flag on the FIRST session with entry from the SECOND
    response = await client.post("/api/v1/injury-flags", json=_flag(
        db_client.id, session.id,
        session_entry_id=entry_id,
    ))
    assert response.status_code == 422
    assert "Session entry does not belong to this session" in response.json()["error"]["message"]
