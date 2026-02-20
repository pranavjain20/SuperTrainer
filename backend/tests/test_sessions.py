import uuid

import pytest

from app.models import Client, Trainer

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture
async def trainer_and_client(db_session):
    """Create a trainer + client for session tests."""
    trainer = Trainer(email=f"sess-trainer-{uuid.uuid4().hex[:8]}@test.com", name="Session Trainer")
    db_session.add(trainer)
    await db_session.flush()

    client = Client(trainer_id=trainer.id, name="Session Client")
    db_session.add(client)
    await db_session.flush()

    # Set temp trainer ID for API
    from app.api import clients as clients_module
    clients_module.TEMP_TRAINER_ID = trainer.id

    return trainer, client


# --- Create Session ---


async def test_create_session_success(client, trainer_and_client):
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
    assert "id" in data


async def test_create_session_invalid_client(client, trainer_and_client):
    response = await client.post("/api/v1/sessions", json={
        "client_id": str(uuid.uuid4()),
        "started_at": "2026-02-19T10:00:00Z",
    })
    assert response.status_code == 404


async def test_create_session_missing_fields(client, trainer_and_client):
    response = await client.post("/api/v1/sessions", json={})
    assert response.status_code == 422


# --- Get Session ---


async def test_get_session_success(client, trainer_and_client):
    _, db_client = trainer_and_client
    create_resp = await client.post("/api/v1/sessions", json={
        "client_id": str(db_client.id),
        "started_at": "2026-02-19T11:00:00Z",
    })
    session_id = create_resp.json()["data"]["id"]

    response = await client.get(f"/api/v1/sessions/{session_id}")
    assert response.status_code == 200
    assert response.json()["data"]["id"] == session_id


async def test_get_session_not_found(client, trainer_and_client):
    response = await client.get(f"/api/v1/sessions/{uuid.uuid4()}")
    assert response.status_code == 404


# --- List Sessions by Client ---


async def test_list_client_sessions(client, trainer_and_client):
    _, db_client = trainer_and_client
    # Create 2 sessions
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


async def test_list_sessions_for_nonexistent_client(client, trainer_and_client):
    response = await client.get(f"/api/v1/clients/{uuid.uuid4()}/sessions")
    assert response.status_code == 404


async def test_list_sessions_empty_for_new_client(client, trainer_and_client):
    # Create a fresh client with no sessions
    create_resp = await client.post("/api/v1/clients", json={"name": "No Sessions"})
    new_client_id = create_resp.json()["data"]["id"]

    response = await client.get(f"/api/v1/clients/{new_client_id}/sessions")
    assert response.status_code == 200
    assert response.json()["data"] == []


# --- Update Session ---


async def test_update_session_success(client, trainer_and_client):
    _, db_client = trainer_and_client
    create_resp = await client.post("/api/v1/sessions", json={
        "client_id": str(db_client.id),
        "started_at": "2026-02-19T10:00:00Z",
    })
    session_id = create_resp.json()["data"]["id"]

    response = await client.patch(f"/api/v1/sessions/{session_id}", json={
        "ended_at": "2026-02-19T11:00:00Z",
        "duration_minutes": 60,
        "raw_transcript": "Some transcript text",
        "processing_status": "completed",
        "trainer_edited": True,
    })
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["duration_minutes"] == 60
    assert data["raw_transcript"] == "Some transcript text"
    assert data["processing_status"] == "completed"
    assert data["trainer_edited"] is True


async def test_update_session_partial(client, trainer_and_client):
    _, db_client = trainer_and_client
    create_resp = await client.post("/api/v1/sessions", json={
        "client_id": str(db_client.id),
        "started_at": "2026-02-19T10:00:00Z",
    })
    session_id = create_resp.json()["data"]["id"]

    # Update only one field
    response = await client.patch(f"/api/v1/sessions/{session_id}", json={
        "duration_minutes": 45,
    })
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["duration_minutes"] == 45
    # Other fields unchanged
    assert data["processing_status"] == "pending"
    assert data["trainer_edited"] is False
    assert data["raw_transcript"] is None


async def test_update_session_not_found(client, trainer_and_client):
    response = await client.patch(f"/api/v1/sessions/{uuid.uuid4()}", json={
        "duration_minutes": 60,
    })
    assert response.status_code == 404


# --- Delete Session ---


async def test_delete_session_success(client, trainer_and_client):
    _, db_client = trainer_and_client
    create_resp = await client.post("/api/v1/sessions", json={
        "client_id": str(db_client.id),
        "started_at": "2026-02-19T12:00:00Z",
    })
    session_id = create_resp.json()["data"]["id"]

    response = await client.delete(f"/api/v1/sessions/{session_id}")
    assert response.status_code == 204

    # Verify it's gone
    get_resp = await client.get(f"/api/v1/sessions/{session_id}")
    assert get_resp.status_code == 404


async def test_delete_session_not_found(client, trainer_and_client):
    response = await client.delete(f"/api/v1/sessions/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_delete_session_cascades_exercise_logs(client, trainer_and_client):
    _, db_client = trainer_and_client
    # Create session
    create_resp = await client.post("/api/v1/sessions", json={
        "client_id": str(db_client.id),
        "started_at": "2026-02-19T13:00:00Z",
    })
    session_id = create_resp.json()["data"]["id"]

    # Create exercise log on that session
    await client.post("/api/v1/exercise-logs", json={
        "session_id": session_id,
        "exercise_name": "Bench Press",
    })

    # Verify exercise log exists via client endpoint
    logs_before = await client.get(f"/api/v1/clients/{db_client.id}/exercise-logs")
    bench_logs = [l for l in logs_before.json()["data"] if l["exercise_name"] == "Bench Press"]
    assert len(bench_logs) >= 1

    # Delete session — cascade should remove exercise logs
    delete_resp = await client.delete(f"/api/v1/sessions/{session_id}")
    assert delete_resp.status_code == 204

    # Verify exercise logs are gone via client endpoint
    logs_after = await client.get(f"/api/v1/clients/{db_client.id}/exercise-logs")
    remaining_session_logs = [
        l for l in logs_after.json()["data"] if l["session_id"] == session_id
    ]
    assert remaining_session_logs == []


async def test_delete_session_cascades_injury_flags(client, trainer_and_client):
    _, db_client = trainer_and_client
    # Create session
    create_resp = await client.post("/api/v1/sessions", json={
        "client_id": str(db_client.id),
        "started_at": "2026-02-19T14:00:00Z",
    })
    session_id = create_resp.json()["data"]["id"]

    # Create injury flag on that session
    await client.post("/api/v1/injury-flags", json={
        "client_id": str(db_client.id),
        "session_id": session_id,
        "body_part": "left knee",
        "pain_level": 5,
    })

    # Verify injury flag exists
    flags_before = await client.get(f"/api/v1/clients/{db_client.id}/injury-flags")
    knee_flags = [f for f in flags_before.json()["data"] if f["session_id"] == session_id]
    assert len(knee_flags) >= 1

    # Delete session — cascade should remove injury flags
    delete_resp = await client.delete(f"/api/v1/sessions/{session_id}")
    assert delete_resp.status_code == 204

    # Verify injury flags for that session are gone
    flags_after = await client.get(f"/api/v1/clients/{db_client.id}/injury-flags")
    remaining_session_flags = [
        f for f in flags_after.json()["data"] if f["session_id"] == session_id
    ]
    assert remaining_session_flags == []
