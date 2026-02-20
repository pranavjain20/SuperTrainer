import uuid

import pytest

from app.models import Client, Trainer

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture
async def trainer_client_session(client, db_session):
    """Create trainer + client + session for injury flag tests."""
    trainer = Trainer(email=f"iflag-trainer-{uuid.uuid4().hex[:8]}@test.com", name="IFlag Trainer")
    db_session.add(trainer)
    await db_session.flush()

    db_client = Client(trainer_id=trainer.id, name="IFlag Client")
    db_session.add(db_client)
    await db_session.flush()

    from app.api import clients as clients_module
    clients_module.TEMP_TRAINER_ID = trainer.id

    resp = await client.post("/api/v1/sessions", json={
        "client_id": str(db_client.id),
        "started_at": "2026-02-19T10:00:00Z",
    })
    session_data = resp.json()["data"]

    return trainer, db_client, session_data


# --- Create Injury Flag ---


async def test_create_injury_flag_success(client, trainer_client_session):
    _, db_client, session_data = trainer_client_session
    response = await client.post("/api/v1/injury-flags", json={
        "client_id": str(db_client.id),
        "session_id": session_data["id"],
        "body_part": "left knee",
        "pain_level": 5,
        "description": "Sharp pain during squats",
    })
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["body_part"] == "left knee"
    assert data["pain_level"] == 5
    assert data["description"] == "Sharp pain during squats"
    assert data["resolved"] is False
    assert data["occurrence_count"] == 1
    assert "id" in data


async def test_create_injury_flag_minimal(client, trainer_client_session):
    _, db_client, session_data = trainer_client_session
    response = await client.post("/api/v1/injury-flags", json={
        "client_id": str(db_client.id),
        "session_id": session_data["id"],
        "body_part": "right shoulder",
        "pain_level": 3,
    })
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["body_part"] == "right shoulder"
    assert data["description"] is None


async def test_create_injury_flag_invalid_client(client, trainer_client_session):
    _, _, session_data = trainer_client_session
    response = await client.post("/api/v1/injury-flags", json={
        "client_id": str(uuid.uuid4()),
        "session_id": session_data["id"],
        "body_part": "knee",
        "pain_level": 5,
    })
    assert response.status_code == 404


async def test_create_injury_flag_invalid_session(client, trainer_client_session):
    _, db_client, _ = trainer_client_session
    response = await client.post("/api/v1/injury-flags", json={
        "client_id": str(db_client.id),
        "session_id": str(uuid.uuid4()),
        "body_part": "knee",
        "pain_level": 5,
    })
    assert response.status_code == 404


async def test_create_injury_flag_with_exercise_log(client, trainer_client_session):
    _, db_client, session_data = trainer_client_session
    # Create an exercise log first
    log_resp = await client.post("/api/v1/exercise-logs", json={
        "session_id": session_data["id"],
        "exercise_name": "Squat",
    })
    log_id = log_resp.json()["data"]["id"]

    response = await client.post("/api/v1/injury-flags", json={
        "client_id": str(db_client.id),
        "session_id": session_data["id"],
        "exercise_log_id": log_id,
        "body_part": "left knee",
        "pain_level": 7,
        "description": "Pain during squats specifically",
    })
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["exercise_log_id"] == log_id
    assert data["body_part"] == "left knee"


async def test_create_injury_flag_nonexistent_exercise_log(client, trainer_client_session):
    _, db_client, session_data = trainer_client_session
    response = await client.post("/api/v1/injury-flags", json={
        "client_id": str(db_client.id),
        "session_id": session_data["id"],
        "exercise_log_id": str(uuid.uuid4()),
        "body_part": "knee",
        "pain_level": 5,
    })
    assert response.status_code == 404


async def test_create_injury_flag_session_client_mismatch(client, trainer_client_session, db_session):
    _, db_client, session_data = trainer_client_session
    # Create a second client
    other_client_resp = await client.post("/api/v1/clients", json={"name": "Other Client"})
    other_client_id = other_client_resp.json()["data"]["id"]

    # Try to create injury flag with other_client + original session (which belongs to db_client)
    response = await client.post("/api/v1/injury-flags", json={
        "client_id": other_client_id,
        "session_id": session_data["id"],
        "body_part": "knee",
        "pain_level": 5,
    })
    assert response.status_code == 422
    assert "does not belong" in response.json()["detail"]


async def test_create_injury_flag_exercise_log_session_mismatch(client, trainer_client_session):
    _, db_client, session_data = trainer_client_session
    # Create a second session
    second_session_resp = await client.post("/api/v1/sessions", json={
        "client_id": str(db_client.id),
        "started_at": "2026-02-20T10:00:00Z",
    })
    second_session_id = second_session_resp.json()["data"]["id"]

    # Create exercise log on the SECOND session
    log_resp = await client.post("/api/v1/exercise-logs", json={
        "session_id": second_session_id,
        "exercise_name": "Bench Press",
    })
    log_id = log_resp.json()["data"]["id"]

    # Try to create injury flag on FIRST session with exercise log from SECOND session
    response = await client.post("/api/v1/injury-flags", json={
        "client_id": str(db_client.id),
        "session_id": session_data["id"],
        "exercise_log_id": log_id,
        "body_part": "shoulder",
        "pain_level": 4,
    })
    assert response.status_code == 422
    assert "does not belong" in response.json()["detail"]


async def test_create_injury_flag_missing_fields(client, trainer_client_session):
    response = await client.post("/api/v1/injury-flags", json={})
    assert response.status_code == 422


async def test_create_injury_flag_pain_level_too_low(client, trainer_client_session):
    _, db_client, session_data = trainer_client_session
    response = await client.post("/api/v1/injury-flags", json={
        "client_id": str(db_client.id),
        "session_id": session_data["id"],
        "body_part": "knee",
        "pain_level": 0,
    })
    assert response.status_code == 422


async def test_create_injury_flag_pain_level_too_high(client, trainer_client_session):
    _, db_client, session_data = trainer_client_session
    response = await client.post("/api/v1/injury-flags", json={
        "client_id": str(db_client.id),
        "session_id": session_data["id"],
        "body_part": "knee",
        "pain_level": 11,
    })
    assert response.status_code == 422


# --- List Injury Flags by Client ---


async def test_list_injury_flags_by_client(client, trainer_client_session):
    _, db_client, session_data = trainer_client_session
    # Create 2 injury flags
    await client.post("/api/v1/injury-flags", json={
        "client_id": str(db_client.id),
        "session_id": session_data["id"],
        "body_part": "left knee",
        "pain_level": 4,
    })
    await client.post("/api/v1/injury-flags", json={
        "client_id": str(db_client.id),
        "session_id": session_data["id"],
        "body_part": "lower back",
        "pain_level": 6,
    })

    response = await client.get(f"/api/v1/clients/{db_client.id}/injury-flags")
    assert response.status_code == 200
    flags = response.json()["data"]
    assert len(flags) >= 2
    body_parts = [f["body_part"] for f in flags]
    assert "left knee" in body_parts
    assert "lower back" in body_parts


async def test_list_injury_flags_empty(client, trainer_client_session):
    trainer, _, _ = trainer_client_session
    # Create a fresh client with no injury flags
    create_resp = await client.post("/api/v1/clients", json={"name": "Healthy Client"})
    new_client_id = create_resp.json()["data"]["id"]

    response = await client.get(f"/api/v1/clients/{new_client_id}/injury-flags")
    assert response.status_code == 200
    assert response.json()["data"] == []


async def test_list_injury_flags_nonexistent_client(client, trainer_client_session):
    response = await client.get(f"/api/v1/clients/{uuid.uuid4()}/injury-flags")
    assert response.status_code == 404
