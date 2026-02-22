import uuid
from datetime import datetime, timezone

import pytest

from app.models import Client, Session, SessionPlan, Trainer

pytestmark = pytest.mark.asyncio(loop_scope="session")


# --- Create Session ---


async def test_create_session_valid(client, trainer_and_client):
    _, db_client = trainer_and_client
    response = await client.post("/api/v1/sessions", json={
        "client_id": str(db_client.id),
        "started_at": "2026-02-19T10:00:00Z",
    })
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["client_id"] == str(db_client.id)
    assert data["processing_status"] == "pending"
    assert data["trainer_edited"] is False
    assert data["scheduled_for"] is None
    assert data["plan_id"] is None
    assert "id" in data


async def test_create_session_with_scheduled_for(client, trainer_and_client):
    _, db_client = trainer_and_client
    response = await client.post("/api/v1/sessions", json={
        "client_id": str(db_client.id),
        "started_at": "2026-02-20T09:00:00Z",
        "scheduled_for": "2026-02-20T09:00:00Z",
    })
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["scheduled_for"] is not None


async def test_create_session_with_plan_id(client, trainer_and_client, db_session):
    trainer, db_client = trainer_and_client

    # Create a session plan directly in DB
    plan = SessionPlan(
        client_id=db_client.id,
        trainer_id=trainer.id,
        plan_text="Leg day: squats 5x5, lunges 3x12",
    )
    db_session.add(plan)
    await db_session.flush()

    response = await client.post("/api/v1/sessions", json={
        "client_id": str(db_client.id),
        "started_at": "2026-02-20T10:00:00Z",
        "plan_id": str(plan.id),
    })
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["plan_id"] == str(plan.id)


async def test_create_session_invalid_client_404(client, trainer_and_client):
    response = await client.post("/api/v1/sessions", json={
        "client_id": str(uuid.uuid4()),
        "started_at": "2026-02-19T10:00:00Z",
    })
    assert response.status_code == 404


async def test_create_session_invalid_plan_id_404(client, trainer_and_client):
    _, db_client = trainer_and_client
    response = await client.post("/api/v1/sessions", json={
        "client_id": str(db_client.id),
        "started_at": "2026-02-19T10:00:00Z",
        "plan_id": str(uuid.uuid4()),
    })
    assert response.status_code == 404


async def test_create_session_missing_fields_422(client, trainer_and_client):
    response = await client.post("/api/v1/sessions", json={})
    assert response.status_code == 422


# --- Get Session ---


async def test_get_session_found(client, trainer_and_client, db_session):
    trainer, db_client = trainer_and_client

    # Create with plan and scheduled_for to verify they appear in response
    plan = SessionPlan(
        client_id=db_client.id,
        trainer_id=trainer.id,
        plan_text="Pull day plan",
    )
    db_session.add(plan)
    await db_session.flush()

    create_resp = await client.post("/api/v1/sessions", json={
        "client_id": str(db_client.id),
        "started_at": "2026-02-19T11:00:00Z",
        "scheduled_for": "2026-02-19T11:00:00Z",
        "plan_id": str(plan.id),
    })
    session_id = create_resp.json()["data"]["id"]

    response = await client.get(f"/api/v1/sessions/{session_id}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == session_id
    assert data["scheduled_for"] is not None
    assert data["plan_id"] == str(plan.id)


async def test_get_session_not_found_404(client, trainer_and_client):
    response = await client.get(f"/api/v1/sessions/{uuid.uuid4()}")
    assert response.status_code == 404


# --- List Sessions by Client ---


async def test_list_sessions_returns_sessions(client, trainer_and_client):
    _, db_client = trainer_and_client
    await client.post("/api/v1/sessions", json={
        "client_id": str(db_client.id),
        "started_at": "2026-02-18T09:00:00Z",
    })
    await client.post("/api/v1/sessions", json={
        "client_id": str(db_client.id),
        "started_at": "2026-02-19T09:00:00Z",
    })

    response = await client.get(f"/api/v1/clients/{db_client.id}/sessions")
    assert response.status_code == 200
    sessions = response.json()["data"]
    assert len(sessions) >= 2
    # Newest first
    dates = [s["started_at"] for s in sessions]
    assert dates == sorted(dates, reverse=True)


async def test_list_sessions_empty(client, trainer_and_client):
    # Create a fresh client with no sessions
    create_resp = await client.post("/api/v1/clients", json={"name": "No Sessions Client"})
    new_client_id = create_resp.json()["data"]["id"]

    response = await client.get(f"/api/v1/clients/{new_client_id}/sessions")
    assert response.status_code == 200
    assert response.json()["data"] == []


async def test_list_sessions_pagination(client, trainer_and_client):
    # Create a fresh client to get clean pagination
    create_resp = await client.post("/api/v1/clients", json={"name": "Pagination Client"})
    new_client_id = create_resp.json()["data"]["id"]

    for i in range(3):
        await client.post("/api/v1/sessions", json={
            "client_id": new_client_id,
            "started_at": f"2026-02-{15 + i}T09:00:00Z",
        })

    page1 = await client.get(
        f"/api/v1/clients/{new_client_id}/sessions", params={"limit": 2},
    )
    assert page1.status_code == 200
    page1_data = page1.json()
    assert len(page1_data["data"]) == 2
    assert page1_data["meta"]["has_more"] is True
    cursor = page1_data["meta"]["cursor"]

    page2 = await client.get(
        f"/api/v1/clients/{new_client_id}/sessions",
        params={"limit": 2, "cursor": cursor},
    )
    assert page2.status_code == 200
    page2_data = page2.json()
    assert len(page2_data["data"]) >= 1

    page1_ids = {s["id"] for s in page1_data["data"]}
    page2_ids = {s["id"] for s in page2_data["data"]}
    assert page1_ids.isdisjoint(page2_ids)


# --- Update Session ---


async def test_update_session_valid(client, trainer_and_client):
    _, db_client = trainer_and_client
    create_resp = await client.post("/api/v1/sessions", json={
        "client_id": str(db_client.id),
        "started_at": "2026-02-19T10:00:00Z",
    })
    session_id = create_resp.json()["data"]["id"]

    response = await client.patch(f"/api/v1/sessions/{session_id}", json={
        "ended_at": "2026-02-19T11:00:00Z",
        "duration_minutes": 60,
        "raw_transcript": "Bench press, 5x5 at 80kg",
        "processing_status": "completed",
        "trainer_edited": True,
    })
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["duration_minutes"] == 60
    assert data["raw_transcript"] == "Bench press, 5x5 at 80kg"
    assert data["processing_status"] == "completed"
    assert data["trainer_edited"] is True


async def test_update_session_partial_preserves_unchanged(client, trainer_and_client):
    _, db_client = trainer_and_client
    create_resp = await client.post("/api/v1/sessions", json={
        "client_id": str(db_client.id),
        "started_at": "2026-02-19T10:00:00Z",
    })
    session_id = create_resp.json()["data"]["id"]

    response = await client.patch(f"/api/v1/sessions/{session_id}", json={
        "duration_minutes": 45,
    })
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["duration_minutes"] == 45
    assert data["processing_status"] == "pending"
    assert data["trainer_edited"] is False
    assert data["raw_transcript"] is None


async def test_update_session_scheduled_for(client, trainer_and_client):
    _, db_client = trainer_and_client
    create_resp = await client.post("/api/v1/sessions", json={
        "client_id": str(db_client.id),
        "started_at": "2026-02-19T10:00:00Z",
    })
    session_id = create_resp.json()["data"]["id"]

    response = await client.patch(f"/api/v1/sessions/{session_id}", json={
        "scheduled_for": "2026-02-25T10:00:00Z",
    })
    assert response.status_code == 200
    assert response.json()["data"]["scheduled_for"] is not None


async def test_update_session_not_found_404(client, trainer_and_client):
    response = await client.patch(f"/api/v1/sessions/{uuid.uuid4()}", json={
        "duration_minutes": 60,
    })
    assert response.status_code == 404


async def test_update_session_invalid_status_422(client, trainer_and_client):
    _, db_client = trainer_and_client
    create_resp = await client.post("/api/v1/sessions", json={
        "client_id": str(db_client.id),
        "started_at": "2026-02-19T10:00:00Z",
    })
    session_id = create_resp.json()["data"]["id"]

    response = await client.patch(f"/api/v1/sessions/{session_id}", json={
        "processing_status": "invalid_status",
    })
    assert response.status_code == 422


# --- Delete Session ---


async def test_delete_session_success_204(client, trainer_and_client):
    _, db_client = trainer_and_client
    create_resp = await client.post("/api/v1/sessions", json={
        "client_id": str(db_client.id),
        "started_at": "2026-02-19T12:00:00Z",
    })
    session_id = create_resp.json()["data"]["id"]

    response = await client.delete(f"/api/v1/sessions/{session_id}")
    assert response.status_code == 204


async def test_delete_session_not_found_404(client, trainer_and_client):
    response = await client.delete(f"/api/v1/sessions/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_delete_session_verify_gone(client, trainer_and_client):
    _, db_client = trainer_and_client
    create_resp = await client.post("/api/v1/sessions", json={
        "client_id": str(db_client.id),
        "started_at": "2026-02-19T13:00:00Z",
    })
    session_id = create_resp.json()["data"]["id"]

    await client.delete(f"/api/v1/sessions/{session_id}")
    get_resp = await client.get(f"/api/v1/sessions/{session_id}")
    assert get_resp.status_code == 404


# --- Cross-Trainer Ownership ---


async def test_create_session_other_trainers_plan_404(client, trainer_and_client, db_session):
    """Creating a session with another trainer's plan should return 404."""
    _, db_client = trainer_and_client

    other_trainer = Trainer(
        email=f"other-sp-{uuid.uuid4().hex[:8]}@test.com", name="Other SP Trainer",
    )
    db_session.add(other_trainer)
    await db_session.flush()

    other_client = Client(trainer_id=other_trainer.id, name="Other SP Client")
    db_session.add(other_client)
    await db_session.flush()

    other_plan = SessionPlan(
        client_id=other_client.id,
        trainer_id=other_trainer.id,
        plan_text="Stolen plan",
    )
    db_session.add(other_plan)
    await db_session.flush()

    response = await client.post("/api/v1/sessions", json={
        "client_id": str(db_client.id),
        "started_at": "2026-02-19T10:00:00Z",
        "plan_id": str(other_plan.id),
    })
    assert response.status_code == 404


async def test_create_session_other_trainers_client_404(client, trainer_and_client, db_session):
    """Creating a session for another trainer's client should return 404."""
    other_trainer = Trainer(
        email=f"other-sc-{uuid.uuid4().hex[:8]}@test.com", name="Other SC Trainer",
    )
    db_session.add(other_trainer)
    await db_session.flush()

    other_client = Client(trainer_id=other_trainer.id, name="Other SC Client")
    db_session.add(other_client)
    await db_session.flush()

    response = await client.post("/api/v1/sessions", json={
        "client_id": str(other_client.id),
        "started_at": "2026-02-19T10:00:00Z",
    })
    assert response.status_code == 404


async def test_get_other_trainers_session_404(client, trainer_and_client, db_session):
    """Getting a session owned by another trainer should return 404."""
    other_trainer = Trainer(
        email=f"other-sg-{uuid.uuid4().hex[:8]}@test.com", name="Other SG Trainer",
    )
    db_session.add(other_trainer)
    await db_session.flush()

    other_client = Client(trainer_id=other_trainer.id, name="Other SG Client")
    db_session.add(other_client)
    await db_session.flush()

    other_session = Session(
        trainer_id=other_trainer.id,
        client_id=other_client.id,
        started_at=datetime(2026, 2, 19, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(other_session)
    await db_session.flush()

    response = await client.get(f"/api/v1/sessions/{other_session.id}")
    assert response.status_code == 404


async def test_update_other_trainers_session_404(client, trainer_and_client, db_session):
    """Updating a session owned by another trainer should return 404."""
    other_trainer = Trainer(
        email=f"other-su-{uuid.uuid4().hex[:8]}@test.com", name="Other SU Trainer",
    )
    db_session.add(other_trainer)
    await db_session.flush()

    other_client = Client(trainer_id=other_trainer.id, name="Other SU Client")
    db_session.add(other_client)
    await db_session.flush()

    other_session = Session(
        trainer_id=other_trainer.id,
        client_id=other_client.id,
        started_at=datetime(2026, 2, 19, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(other_session)
    await db_session.flush()

    response = await client.patch(
        f"/api/v1/sessions/{other_session.id}",
        json={"duration_minutes": 999},
    )
    assert response.status_code == 404


async def test_delete_other_trainers_session_404(client, trainer_and_client, db_session):
    """Deleting a session owned by another trainer should return 404."""
    other_trainer = Trainer(
        email=f"other-sd-{uuid.uuid4().hex[:8]}@test.com", name="Other SD Trainer",
    )
    db_session.add(other_trainer)
    await db_session.flush()

    other_client = Client(trainer_id=other_trainer.id, name="Other SD Client")
    db_session.add(other_client)
    await db_session.flush()

    other_session = Session(
        trainer_id=other_trainer.id,
        client_id=other_client.id,
        started_at=datetime(2026, 2, 19, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(other_session)
    await db_session.flush()

    response = await client.delete(f"/api/v1/sessions/{other_session.id}")
    assert response.status_code == 404


async def test_list_other_trainers_client_sessions_404(client, trainer_and_client, db_session):
    """Listing sessions for another trainer's client via client endpoint should 404."""
    other_trainer = Trainer(
        email=f"other-sl-{uuid.uuid4().hex[:8]}@test.com", name="Other SL Trainer",
    )
    db_session.add(other_trainer)
    await db_session.flush()

    other_client = Client(trainer_id=other_trainer.id, name="Other SL Client")
    db_session.add(other_client)
    await db_session.flush()

    response = await client.get(f"/api/v1/clients/{other_client.id}/sessions")
    assert response.status_code == 404
