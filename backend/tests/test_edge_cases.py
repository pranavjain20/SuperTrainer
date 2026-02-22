"""Edge case tests.

Empty PATCH bodies, pagination boundaries, validation gaps,
and cross-type contamination scenarios.
"""

import uuid

import pytest

from app.models import SessionPlan

pytestmark = pytest.mark.asyncio(loop_scope="session")


# --- Helpers ---


def _exercise_card(**overrides):
    base = {"entry_type": "exercise_card", "exercise_name": "Bench Press"}
    base.update(overrides)
    return base


def _observation_card(**overrides):
    base = {"entry_type": "observation_card", "observation_text": "Looked tired"}
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


# --- Empty PATCH {} (idempotency) ---


async def test_client_patch_empty_body_idempotent(client, trainer_and_client):
    """PATCH /clients/{id} with {} should return 200, no changes."""
    _, db_client = trainer_and_client
    response = await client.patch(f"/api/v1/clients/{db_client.id}", json={})
    assert response.status_code == 200
    assert response.json()["data"]["name"] == db_client.name


async def test_session_patch_empty_body_idempotent(client, trainer_and_client):
    """PATCH /sessions/{id} with {} should return 200, no changes."""
    _, db_client = trainer_and_client
    create_resp = await client.post("/api/v1/sessions", json={
        "client_id": str(db_client.id),
        "started_at": "2026-02-22T10:00:00Z",
    })
    session_id = create_resp.json()["data"]["id"]

    response = await client.patch(f"/api/v1/sessions/{session_id}", json={})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["processing_status"] == "pending"
    assert data["trainer_edited"] is False


async def test_entry_patch_empty_body_idempotent(client, trainer_client_session):
    """PATCH /entries/{id} with {} should return 200, no changes."""
    _, _, session = trainer_client_session
    create_resp = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json=_exercise_card(exercise_name="Squat"),
    )
    entry_id = create_resp.json()["data"]["id"]

    response = await client.patch(f"/api/v1/entries/{entry_id}", json={})
    assert response.status_code == 200
    assert response.json()["data"]["exercise_name"] == "Squat"


async def test_plan_patch_empty_body_idempotent(client, trainer_and_client, db_session):
    """PATCH /plans/{id} with {} should return 200, no changes."""
    trainer, db_client = trainer_and_client
    plan = SessionPlan(
        client_id=db_client.id,
        trainer_id=trainer.id,
        plan_text="Original plan text",
    )
    db_session.add(plan)
    await db_session.flush()

    response = await client.patch(f"/api/v1/plans/{plan.id}", json={})
    assert response.status_code == 200
    assert response.json()["data"]["plan_text"] == "Original plan text"


async def test_injury_flag_patch_empty_body_idempotent(client, trainer_client_session):
    """PATCH /injury-flags/{id} with {} should return 200, no changes."""
    _, db_client, session = trainer_client_session
    create_resp = await client.post(
        "/api/v1/injury-flags",
        json=_flag(db_client.id, session.id, body_part="stable knee"),
    )
    flag_id = create_resp.json()["data"]["id"]

    response = await client.patch(f"/api/v1/injury-flags/{flag_id}", json={})
    assert response.status_code == 200
    assert response.json()["data"]["body_part"] == "stable knee"
    assert response.json()["data"]["pain_level"] == 5


# --- Pagination edge cases ---


async def test_pagination_limit_zero_returns_results(client, trainer_and_client):
    """limit=0 should still return at least one row (no server crash)."""
    _, db_client = trainer_and_client
    # Ensure at least one session exists
    await client.post("/api/v1/sessions", json={
        "client_id": str(db_client.id),
        "started_at": "2026-02-22T09:00:00Z",
    })

    response = await client.get(
        f"/api/v1/clients/{db_client.id}/sessions",
        params={"limit": 0},
    )
    # Should not 500 — behavior may vary but must not crash
    assert response.status_code == 200


async def test_pagination_negative_limit_returns_results(client, trainer_and_client):
    """limit=-1 should not crash the server."""
    _, db_client = trainer_and_client
    await client.post("/api/v1/sessions", json={
        "client_id": str(db_client.id),
        "started_at": "2026-02-22T08:00:00Z",
    })

    response = await client.get(
        f"/api/v1/clients/{db_client.id}/sessions",
        params={"limit": -1},
    )
    # Should not 500
    assert response.status_code == 200


async def test_pagination_stale_cursor_does_not_500(client, trainer_and_client):
    """A cursor UUID that doesn't match any row should return results, not 500."""
    _, db_client = trainer_and_client
    await client.post("/api/v1/sessions", json={
        "client_id": str(db_client.id),
        "started_at": "2026-02-22T07:00:00Z",
    })

    stale_cursor = str(uuid.uuid4())
    response = await client.get(
        f"/api/v1/clients/{db_client.id}/sessions",
        params={"cursor": stale_cursor},
    )
    # A stale cursor should not crash; it returns all results since cursor is not found
    assert response.status_code == 200


# --- Cross-type contamination on entry PATCH ---


async def test_entry_patch_exercise_card_with_observation_text_no_entry_type(
    client, trainer_client_session,
):
    """PATCHing an exercise_card with observation_text (without sending entry_type)
    is rejected at the route level — the handler checks the entry's actual type."""
    _, _, session = trainer_client_session
    create_resp = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json=_exercise_card(exercise_name="Squat"),
    )
    entry_id = create_resp.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/entries/{entry_id}",
        json={"observation_text": "sneaky observation"},
    )
    assert response.status_code == 422


async def test_entry_patch_observation_card_with_exercise_name_no_entry_type(
    client, trainer_client_session,
):
    """PATCHing an observation_card with exercise_name (without entry_type) → 422."""
    _, _, session = trainer_client_session
    create_resp = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json=_observation_card(observation_text="Good energy today"),
    )
    entry_id = create_resp.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/entries/{entry_id}",
        json={"exercise_name": "Squat"},
    )
    assert response.status_code == 422


async def test_entry_patch_with_explicit_wrong_type_422(
    client, trainer_client_session,
):
    """PATCHing an exercise_card with observation_text AND entry_type=exercise_card
    should 422 — schema validates when entry_type is explicitly provided."""
    _, _, session = trainer_client_session
    create_resp = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json=_exercise_card(exercise_name="Bench"),
    )
    entry_id = create_resp.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/entries/{entry_id}",
        json={"entry_type": "exercise_card", "observation_text": "should fail"},
    )
    assert response.status_code == 422


# --- Validation gaps ---


async def test_injury_flag_patch_pain_level_11_422(client, trainer_client_session):
    """PATCH with pain_level=11 should fail validation (upper bound)."""
    _, db_client, session = trainer_client_session
    create_resp = await client.post(
        "/api/v1/injury-flags",
        json=_flag(db_client.id, session.id),
    )
    flag_id = create_resp.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/injury-flags/{flag_id}",
        json={"pain_level": 11},
    )
    assert response.status_code == 422


async def test_error_response_body_structure_404(client, trainer_and_client):
    """404 responses should have {"error": {"code": ..., "message": ...}} structure."""
    response = await client.get(f"/api/v1/clients/{uuid.uuid4()}")
    assert response.status_code == 404
    body = response.json()
    assert "error" in body
    assert "code" in body["error"]
    assert "message" in body["error"]
    assert body["error"]["code"] == "http_404"


async def test_error_response_body_structure_422(client, trainer_and_client):
    """422 responses should have {"error": {"code": ..., "message": ...}} structure."""
    response = await client.post("/api/v1/clients", json={"name": ""})
    assert response.status_code == 422
    body = response.json()
    assert "error" in body
    assert "code" in body["error"]
    assert "message" in body["error"]
    assert body["error"]["code"] == "validation_error"


async def test_session_patch_negative_duration_minutes_422(client, trainer_and_client):
    """PATCH with negative duration_minutes should reject with 422."""
    _, db_client = trainer_and_client
    create_resp = await client.post("/api/v1/sessions", json={
        "client_id": str(db_client.id),
        "started_at": "2026-02-22T06:00:00Z",
    })
    session_id = create_resp.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/sessions/{session_id}",
        json={"duration_minutes": -10},
    )
    assert response.status_code == 422
