import uuid

import pytest

from app.models import Trainer

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture
async def trainer_for_api(db_session) -> Trainer:
    """Create a trainer so the API endpoints work."""
    trainer = Trainer(email=f"api-trainer-{uuid.uuid4().hex[:8]}@test.com", name="API Trainer")
    db_session.add(trainer)
    await db_session.flush()

    # Set the temp trainer ID used by the endpoints
    from app.api import clients as clients_module
    clients_module.TEMP_TRAINER_ID = trainer.id
    return trainer


# --- List Clients ---


async def test_list_clients_empty(client, trainer_for_api):
    response = await client.get("/api/v1/clients")
    assert response.status_code == 200
    body = response.json()
    assert body["data"] == []
    assert body["meta"]["has_more"] is False


async def test_list_clients_returns_created(client, trainer_for_api):
    # Create a client first
    await client.post("/api/v1/clients", json={"name": "List Test Client"})
    response = await client.get("/api/v1/clients")
    assert response.status_code == 200
    names = [c["name"] for c in response.json()["data"]]
    assert "List Test Client" in names


# --- Create Client ---


async def test_create_client_success(client, trainer_for_api):
    response = await client.post("/api/v1/clients", json={
        "name": "New Client",
        "email": "new@test.com",
        "goals": ["strength", "flexibility"],
    })
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "New Client"
    assert data["email"] == "new@test.com"
    assert data["goals"] == ["strength", "flexibility"]
    assert data["archived"] is False
    assert "id" in data


async def test_create_client_minimal(client, trainer_for_api):
    response = await client.post("/api/v1/clients", json={"name": "Minimal Client"})
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "Minimal Client"
    assert data["email"] is None


async def test_create_client_missing_name(client, trainer_for_api):
    response = await client.post("/api/v1/clients", json={})
    assert response.status_code == 422


async def test_create_client_empty_name(client, trainer_for_api):
    response = await client.post("/api/v1/clients", json={"name": ""})
    assert response.status_code == 422


# --- Get Client ---


async def test_get_client_success(client, trainer_for_api):
    create_resp = await client.post("/api/v1/clients", json={"name": "Get Test"})
    client_id = create_resp.json()["data"]["id"]

    response = await client.get(f"/api/v1/clients/{client_id}")
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Get Test"


async def test_get_client_not_found(client, trainer_for_api):
    fake_id = uuid.uuid4()
    response = await client.get(f"/api/v1/clients/{fake_id}")
    assert response.status_code == 404


async def test_get_client_invalid_uuid(client, trainer_for_api):
    response = await client.get("/api/v1/clients/not-a-uuid")
    assert response.status_code == 422


# --- Update Client ---


async def test_update_client_success(client, trainer_for_api):
    create_resp = await client.post("/api/v1/clients", json={"name": "Before Update"})
    client_id = create_resp.json()["data"]["id"]

    response = await client.patch(f"/api/v1/clients/{client_id}", json={
        "name": "After Update",
        "goals": ["new goal"],
    })
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "After Update"
    assert data["goals"] == ["new goal"]


async def test_update_client_partial(client, trainer_for_api):
    create_resp = await client.post("/api/v1/clients", json={
        "name": "Partial Update",
        "email": "keep@test.com",
    })
    client_id = create_resp.json()["data"]["id"]

    response = await client.patch(f"/api/v1/clients/{client_id}", json={"name": "New Name"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "New Name"
    assert data["email"] == "keep@test.com"


async def test_update_client_not_found(client, trainer_for_api):
    response = await client.patch(f"/api/v1/clients/{uuid.uuid4()}", json={"name": "X"})
    assert response.status_code == 404


# --- Archive Client ---


async def test_archive_client_success(client, trainer_for_api):
    create_resp = await client.post("/api/v1/clients", json={"name": "To Archive"})
    client_id = create_resp.json()["data"]["id"]

    response = await client.patch(f"/api/v1/clients/{client_id}/archive")
    assert response.status_code == 200
    assert response.json()["data"]["archived"] is True


async def test_archive_client_hidden_from_list(client, trainer_for_api):
    create_resp = await client.post("/api/v1/clients", json={"name": "Hidden Client"})
    client_id = create_resp.json()["data"]["id"]

    await client.patch(f"/api/v1/clients/{client_id}/archive")

    # Default list excludes archived
    list_resp = await client.get("/api/v1/clients")
    ids = [c["id"] for c in list_resp.json()["data"]]
    assert client_id not in ids

    # With include_archived=true, it shows up
    list_resp = await client.get("/api/v1/clients?include_archived=true")
    ids = [c["id"] for c in list_resp.json()["data"]]
    assert client_id in ids


async def test_archive_client_still_gettable(client, trainer_for_api):
    create_resp = await client.post("/api/v1/clients", json={"name": "Still Gettable"})
    client_id = create_resp.json()["data"]["id"]

    await client.patch(f"/api/v1/clients/{client_id}/archive")

    response = await client.get(f"/api/v1/clients/{client_id}")
    assert response.status_code == 200
    assert response.json()["data"]["archived"] is True
