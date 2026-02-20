import uuid
from datetime import datetime, timezone

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
