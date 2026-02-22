import uuid

import pytest

from app.models import Client, Trainer

pytestmark = pytest.mark.asyncio(loop_scope="session")


# --- List Clients ---


async def test_list_clients_empty(client, trainer_for_api):
    response = await client.get("/api/v1/clients")
    assert response.status_code == 200
    body = response.json()
    assert body["data"] == []
    assert body["meta"]["has_more"] is False


async def test_list_clients_returns_created(client, trainer_for_api):
    await client.post("/api/v1/clients", json={"name": "List Test Client"})
    response = await client.get("/api/v1/clients")
    assert response.status_code == 200
    names = [c["name"] for c in response.json()["data"]]
    assert "List Test Client" in names


async def test_list_clients_pagination_with_cursor(client, trainer_for_api):
    for i in range(3):
        await client.post("/api/v1/clients", json={"name": f"Page Client {i}"})

    # Page 1: limit=2
    page1 = await client.get("/api/v1/clients", params={"limit": 2})
    assert page1.status_code == 200
    page1_data = page1.json()
    assert len(page1_data["data"]) == 2
    assert page1_data["meta"]["has_more"] is True
    cursor = page1_data["meta"]["cursor"]
    assert cursor is not None

    # Page 2: use cursor from page 1
    page2 = await client.get("/api/v1/clients", params={"limit": 2, "cursor": cursor})
    assert page2.status_code == 200
    page2_data = page2.json()
    assert len(page2_data["data"]) >= 1

    # No overlap between pages
    page1_ids = {c["id"] for c in page1_data["data"]}
    page2_ids = {c["id"] for c in page2_data["data"]}
    assert page1_ids.isdisjoint(page2_ids)


async def test_list_clients_excludes_archived(client, trainer_for_api):
    resp = await client.post("/api/v1/clients", json={"name": "Will Archive"})
    client_id = resp.json()["data"]["id"]
    await client.patch(f"/api/v1/clients/{client_id}/archive")

    list_resp = await client.get("/api/v1/clients")
    ids = [c["id"] for c in list_resp.json()["data"]]
    assert client_id not in ids


async def test_list_clients_include_archived(client, trainer_for_api):
    resp = await client.post("/api/v1/clients", json={"name": "Archived Visible"})
    client_id = resp.json()["data"]["id"]
    await client.patch(f"/api/v1/clients/{client_id}/archive")

    list_resp = await client.get("/api/v1/clients", params={"include_archived": "true"})
    ids = [c["id"] for c in list_resp.json()["data"]]
    assert client_id in ids


# --- Create Client ---


async def test_create_client_all_fields(client, trainer_for_api):
    response = await client.post("/api/v1/clients", json={
        "name": "Full Client",
        "email": "full@test.com",
        "phone": "555-1234",
        "goals": ["strength", "flexibility"],
        "injury_history": "ACL tear 2024",
    })
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "Full Client"
    assert data["email"] == "full@test.com"
    assert data["phone"] == "555-1234"
    assert data["goals"] == ["strength", "flexibility"]
    assert data["injury_history"] == "ACL tear 2024"
    assert data["archived"] is False
    assert "id" in data


async def test_create_client_minimal(client, trainer_for_api):
    response = await client.post("/api/v1/clients", json={"name": "Minimal"})
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "Minimal"
    assert data["email"] is None
    assert data["phone"] is None
    assert data["goals"] is None


async def test_create_client_empty_goals(client, trainer_for_api):
    """POST client with goals=[] should succeed (no goals set yet)."""
    response = await client.post("/api/v1/clients", json={
        "name": "No Goals Yet",
        "goals": [],
    })
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["goals"] == []
    assert data["name"] == "No Goals Yet"


async def test_create_client_missing_name_422(client, trainer_for_api):
    response = await client.post("/api/v1/clients", json={})
    assert response.status_code == 422


async def test_create_client_empty_name_422(client, trainer_for_api):
    response = await client.post("/api/v1/clients", json={"name": ""})
    assert response.status_code == 422


# --- Get Client ---


async def test_get_client_found(client, trainer_for_api):
    create_resp = await client.post("/api/v1/clients", json={"name": "Get Test"})
    client_id = create_resp.json()["data"]["id"]

    response = await client.get(f"/api/v1/clients/{client_id}")
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Get Test"
    assert response.json()["data"]["id"] == client_id


async def test_get_client_not_found_404(client, trainer_for_api):
    response = await client.get(f"/api/v1/clients/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_get_client_invalid_uuid_422(client, trainer_for_api):
    response = await client.get("/api/v1/clients/not-a-uuid")
    assert response.status_code == 422


# --- Update Client ---


async def test_update_client_success(client, trainer_for_api):
    create_resp = await client.post("/api/v1/clients", json={
        "name": "Before Update",
        "email": "before@test.com",
    })
    client_id = create_resp.json()["data"]["id"]

    response = await client.patch(f"/api/v1/clients/{client_id}", json={
        "name": "After Update",
        "goals": ["new goal"],
    })
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "After Update"
    assert data["goals"] == ["new goal"]


async def test_update_client_partial_preserves_unchanged(client, trainer_for_api):
    create_resp = await client.post("/api/v1/clients", json={
        "name": "Partial Update",
        "email": "keep@test.com",
        "phone": "555-9999",
    })
    client_id = create_resp.json()["data"]["id"]

    response = await client.patch(f"/api/v1/clients/{client_id}", json={"name": "New Name"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "New Name"
    assert data["email"] == "keep@test.com"
    assert data["phone"] == "555-9999"


async def test_update_client_not_found_404(client, trainer_for_api):
    response = await client.patch(f"/api/v1/clients/{uuid.uuid4()}", json={"name": "X"})
    assert response.status_code == 404


async def test_update_client_empty_name_422(client, trainer_for_api):
    create_resp = await client.post("/api/v1/clients", json={"name": "Valid Name"})
    client_id = create_resp.json()["data"]["id"]

    response = await client.patch(f"/api/v1/clients/{client_id}", json={"name": ""})
    assert response.status_code == 422


# --- Archive Client ---


async def test_archive_client_success(client, trainer_for_api):
    create_resp = await client.post("/api/v1/clients", json={"name": "To Archive"})
    client_id = create_resp.json()["data"]["id"]

    response = await client.patch(f"/api/v1/clients/{client_id}/archive")
    assert response.status_code == 200
    assert response.json()["data"]["archived"] is True


async def test_archive_client_hidden_from_list(client, trainer_for_api):
    create_resp = await client.post("/api/v1/clients", json={"name": "Hidden"})
    client_id = create_resp.json()["data"]["id"]
    await client.patch(f"/api/v1/clients/{client_id}/archive")

    list_resp = await client.get("/api/v1/clients")
    ids = [c["id"] for c in list_resp.json()["data"]]
    assert client_id not in ids


async def test_archive_client_still_gettable(client, trainer_for_api):
    create_resp = await client.post("/api/v1/clients", json={"name": "Still Gettable"})
    client_id = create_resp.json()["data"]["id"]
    await client.patch(f"/api/v1/clients/{client_id}/archive")

    response = await client.get(f"/api/v1/clients/{client_id}")
    assert response.status_code == 200
    assert response.json()["data"]["archived"] is True


# --- List Client Sessions ---


async def test_list_client_sessions_not_found_404(client, trainer_for_api):
    response = await client.get(f"/api/v1/clients/{uuid.uuid4()}/sessions")
    assert response.status_code == 404


# --- Cross-Trainer Ownership ---


async def test_get_other_trainers_client_404(client, trainer_for_api, db_session):
    """Getting a client that belongs to another trainer should return 404."""
    other_trainer = Trainer(
        email=f"other-cg-{uuid.uuid4().hex[:8]}@test.com", name="Other CG Trainer",
    )
    db_session.add(other_trainer)
    await db_session.flush()

    other_client = Client(trainer_id=other_trainer.id, name="Other CG Client")
    db_session.add(other_client)
    await db_session.flush()

    response = await client.get(f"/api/v1/clients/{other_client.id}")
    assert response.status_code == 404


async def test_update_other_trainers_client_404(client, trainer_for_api, db_session):
    """Updating a client that belongs to another trainer should return 404."""
    other_trainer = Trainer(
        email=f"other-cu-{uuid.uuid4().hex[:8]}@test.com", name="Other CU Trainer",
    )
    db_session.add(other_trainer)
    await db_session.flush()

    other_client = Client(trainer_id=other_trainer.id, name="Other CU Client")
    db_session.add(other_client)
    await db_session.flush()

    response = await client.patch(
        f"/api/v1/clients/{other_client.id}", json={"name": "Hacked Name"},
    )
    assert response.status_code == 404


async def test_archive_other_trainers_client_404(client, trainer_for_api, db_session):
    """Archiving a client that belongs to another trainer should return 404."""
    other_trainer = Trainer(
        email=f"other-ca-{uuid.uuid4().hex[:8]}@test.com", name="Other CA Trainer",
    )
    db_session.add(other_trainer)
    await db_session.flush()

    other_client = Client(trainer_id=other_trainer.id, name="Other CA Client")
    db_session.add(other_client)
    await db_session.flush()

    response = await client.patch(f"/api/v1/clients/{other_client.id}/archive")
    assert response.status_code == 404


async def test_list_other_trainers_client_sessions_404(client, trainer_for_api, db_session):
    """Listing sessions for another trainer's client should return 404."""
    other_trainer = Trainer(
        email=f"other-cls-{uuid.uuid4().hex[:8]}@test.com", name="Other CLS Trainer",
    )
    db_session.add(other_trainer)
    await db_session.flush()

    other_client = Client(trainer_id=other_trainer.id, name="Other CLS Client")
    db_session.add(other_client)
    await db_session.flush()

    response = await client.get(f"/api/v1/clients/{other_client.id}/sessions")
    assert response.status_code == 404


async def test_list_clients_excludes_other_trainers(client, trainer_for_api, db_session):
    """List should only return the current trainer's clients, not other trainers'."""
    other_trainer = Trainer(
        email=f"other-clst-{uuid.uuid4().hex[:8]}@test.com", name="Other CLST Trainer",
    )
    db_session.add(other_trainer)
    await db_session.flush()

    other_client = Client(trainer_id=other_trainer.id, name="Invisible Client")
    db_session.add(other_client)
    await db_session.flush()

    response = await client.get("/api/v1/clients")
    assert response.status_code == 200
    ids = [c["id"] for c in response.json()["data"]]
    assert str(other_client.id) not in ids
