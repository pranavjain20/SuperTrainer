import uuid

import pytest

from app.models import Client, Trainer

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture
async def trainer_client_session(client, db_session):
    """Create trainer + client + session for exercise log tests."""
    trainer = Trainer(email=f"elog-trainer-{uuid.uuid4().hex[:8]}@test.com", name="ELog Trainer")
    db_session.add(trainer)
    await db_session.flush()

    db_client = Client(trainer_id=trainer.id, name="ELog Client")
    db_session.add(db_client)
    await db_session.flush()

    # Set temp trainer ID for API
    from app.api import clients as clients_module
    clients_module.TEMP_TRAINER_ID = trainer.id

    # Create a session via API
    resp = await client.post("/api/v1/sessions", json={
        "client_id": str(db_client.id),
        "started_at": "2026-02-19T10:00:00Z",
    })
    session_data = resp.json()["data"]

    return trainer, db_client, session_data


# --- Create Exercise Log ---


async def test_create_exercise_log_success(client, trainer_client_session):
    _, _, session_data = trainer_client_session
    response = await client.post("/api/v1/exercise-logs", json={
        "session_id": session_data["id"],
        "exercise_name": "Bench Press",
        "sets": [{"set": 1, "weight_kg": 80, "reps": 8}],
        "total_volume_kg": 640.0,
        "form_notes": ["Good depth"],
        "cues_given": ["Drive through feet"],
    })
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["exercise_name"] == "Bench Press"
    assert data["session_id"] == session_data["id"]
    assert data["total_volume_kg"] == 640.0
    assert data["form_notes"] == ["Good depth"]
    assert data["cues_given"] == ["Drive through feet"]
    assert "id" in data


async def test_create_exercise_log_client_id_derived_from_session(client, trainer_client_session):
    _, db_client, session_data = trainer_client_session
    response = await client.post("/api/v1/exercise-logs", json={
        "session_id": session_data["id"],
        "exercise_name": "Romanian Deadlift",
    })
    assert response.status_code == 201
    data = response.json()["data"]
    # client_id should be auto-derived from the session, not from request body
    assert data["client_id"] == str(db_client.id)


async def test_create_exercise_log_minimal(client, trainer_client_session):
    _, _, session_data = trainer_client_session
    response = await client.post("/api/v1/exercise-logs", json={
        "session_id": session_data["id"],
        "exercise_name": "Squat",
    })
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["exercise_name"] == "Squat"
    assert data["sets"] is None
    assert data["total_volume_kg"] is None


async def test_create_exercise_log_invalid_session(client, trainer_client_session):
    response = await client.post("/api/v1/exercise-logs", json={
        "session_id": str(uuid.uuid4()),
        "exercise_name": "Deadlift",
    })
    assert response.status_code == 404


async def test_create_exercise_log_missing_fields(client, trainer_client_session):
    response = await client.post("/api/v1/exercise-logs", json={})
    assert response.status_code == 422


async def test_create_exercise_log_empty_name(client, trainer_client_session):
    _, _, session_data = trainer_client_session
    response = await client.post("/api/v1/exercise-logs", json={
        "session_id": session_data["id"],
        "exercise_name": "",
    })
    assert response.status_code == 422


# --- List Exercise Logs by Session ---


async def test_list_exercise_logs_by_session(client, trainer_client_session):
    _, _, session_data = trainer_client_session
    # Create 2 exercise logs
    await client.post("/api/v1/exercise-logs", json={
        "session_id": session_data["id"],
        "exercise_name": "Bench Press",
    })
    await client.post("/api/v1/exercise-logs", json={
        "session_id": session_data["id"],
        "exercise_name": "Overhead Press",
    })

    response = await client.get(f"/api/v1/sessions/{session_data['id']}/exercise-logs")
    assert response.status_code == 200
    logs = response.json()["data"]
    assert len(logs) >= 2
    names = [log["exercise_name"] for log in logs]
    assert "Bench Press" in names
    assert "Overhead Press" in names


async def test_list_exercise_logs_empty_session(client, trainer_client_session):
    _, db_client, _ = trainer_client_session
    # Create a new session with no exercise logs
    resp = await client.post("/api/v1/sessions", json={
        "client_id": str(db_client.id),
        "started_at": "2026-02-20T10:00:00Z",
    })
    empty_session_id = resp.json()["data"]["id"]

    response = await client.get(f"/api/v1/sessions/{empty_session_id}/exercise-logs")
    assert response.status_code == 200
    assert response.json()["data"] == []


async def test_list_exercise_logs_nonexistent_session(client, trainer_client_session):
    response = await client.get(f"/api/v1/sessions/{uuid.uuid4()}/exercise-logs")
    assert response.status_code == 404


# --- List Exercise Logs by Client ---


async def test_list_exercise_logs_by_client(client, trainer_client_session):
    _, db_client, session_data = trainer_client_session
    # Ensure at least one exercise log exists
    await client.post("/api/v1/exercise-logs", json={
        "session_id": session_data["id"],
        "exercise_name": "Deadlift",
    })

    response = await client.get(f"/api/v1/clients/{db_client.id}/exercise-logs")
    assert response.status_code == 200
    logs = response.json()["data"]
    assert len(logs) >= 1


async def test_list_exercise_logs_by_client_filtered_by_name(client, trainer_client_session):
    _, db_client, session_data = trainer_client_session
    # Create logs with different names
    await client.post("/api/v1/exercise-logs", json={
        "session_id": session_data["id"],
        "exercise_name": "Squat",
    })
    await client.post("/api/v1/exercise-logs", json={
        "session_id": session_data["id"],
        "exercise_name": "Lunge",
    })

    response = await client.get(
        f"/api/v1/clients/{db_client.id}/exercise-logs",
        params={"exercise_name": "Squat"},
    )
    assert response.status_code == 200
    logs = response.json()["data"]
    assert all(log["exercise_name"] == "Squat" for log in logs)
    assert len(logs) >= 1


async def test_list_exercise_logs_nonexistent_client(client, trainer_client_session):
    response = await client.get(f"/api/v1/clients/{uuid.uuid4()}/exercise-logs")
    assert response.status_code == 404
