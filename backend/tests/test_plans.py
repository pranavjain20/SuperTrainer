import uuid
from datetime import datetime, timezone

import pytest

from app.models import Client, Session, SessionPlan, Trainer

pytestmark = pytest.mark.asyncio(loop_scope="session")


# --- Helpers ---


def _plan(**overrides):
    base = {
        "plan_text": "5x5 squats, 3x10 lunges, 3x12 leg press",
        "planned_for_date": "2026-03-01",
    }
    base.update(overrides)
    return base


# --- Create ---


async def test_create_plan_happy_path(client, trainer_and_client):
    trainer, db_client = trainer_and_client
    payload = _plan(client_id=str(db_client.id))
    response = await client.post("/api/v1/plans", json=payload)
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["plan_text"] == payload["plan_text"]
    assert data["planned_for_date"] == "2026-03-01"
    assert data["client_id"] == str(db_client.id)
    assert data["trainer_id"] == str(trainer.id)
    assert "id" in data


async def test_create_plan_all_fields(client, trainer_and_client):
    _, db_client = trainer_and_client
    payload = _plan(
        client_id=str(db_client.id),
        plan_text="Heavy day: 5x3 deadlifts @RPE 8, 4x8 RDLs",
        planned_for_date="2026-03-15",
    )
    response = await client.post("/api/v1/plans", json=payload)
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["plan_text"] == payload["plan_text"]
    assert data["planned_for_date"] == "2026-03-15"


async def test_create_plan_no_date(client, trainer_and_client):
    _, db_client = trainer_and_client
    payload = {"client_id": str(db_client.id), "plan_text": "Light recovery session"}
    response = await client.post("/api/v1/plans", json=payload)
    assert response.status_code == 201
    assert response.json()["data"]["planned_for_date"] is None


async def test_create_plan_missing_plan_text_422(client, trainer_and_client):
    _, db_client = trainer_and_client
    response = await client.post(
        "/api/v1/plans",
        json={"client_id": str(db_client.id)},
    )
    assert response.status_code == 422


async def test_create_plan_empty_plan_text_422(client, trainer_and_client):
    _, db_client = trainer_and_client
    response = await client.post(
        "/api/v1/plans",
        json={"client_id": str(db_client.id), "plan_text": ""},
    )
    assert response.status_code == 422


async def test_create_plan_client_not_found_404(client, trainer_and_client):
    response = await client.post(
        "/api/v1/plans",
        json=_plan(client_id=str(uuid.uuid4())),
    )
    assert response.status_code == 404


async def test_create_plan_trainer_id_auto_set(client, trainer_and_client):
    trainer, db_client = trainer_and_client
    response = await client.post(
        "/api/v1/plans",
        json=_plan(client_id=str(db_client.id)),
    )
    assert response.status_code == 201
    assert response.json()["data"]["trainer_id"] == str(trainer.id)


# --- List by Client ---


async def test_list_plans_returns_plans(client, trainer_and_client, db_session):
    trainer, _ = trainer_and_client
    fresh_client = Client(trainer_id=trainer.id, name="Plan List Client")
    db_session.add(fresh_client)
    await db_session.flush()

    for i in range(3):
        await client.post(
            "/api/v1/plans",
            json=_plan(client_id=str(fresh_client.id), plan_text=f"Plan {i}"),
        )

    response = await client.get(f"/api/v1/clients/{fresh_client.id}/plans")
    assert response.status_code == 200
    assert len(response.json()["data"]) == 3


async def test_list_plans_ordered_by_created_at_desc(client, trainer_and_client, db_session):
    trainer, _ = trainer_and_client
    fresh_client = Client(trainer_id=trainer.id, name="Plan Order Client")
    db_session.add(fresh_client)
    await db_session.flush()

    for text in ["First", "Second", "Third"]:
        await client.post(
            "/api/v1/plans",
            json=_plan(client_id=str(fresh_client.id), plan_text=text),
        )

    response = await client.get(f"/api/v1/clients/{fresh_client.id}/plans")
    data = response.json()["data"]
    assert data[0]["plan_text"] == "Third"


async def test_list_plans_pagination(client, trainer_and_client, db_session):
    trainer, _ = trainer_and_client
    fresh_client = Client(trainer_id=trainer.id, name="Plan Page Client")
    db_session.add(fresh_client)
    await db_session.flush()

    for i in range(4):
        await client.post(
            "/api/v1/plans",
            json=_plan(client_id=str(fresh_client.id), plan_text=f"Plan {i}"),
        )

    page1 = await client.get(
        f"/api/v1/clients/{fresh_client.id}/plans", params={"limit": 2},
    )
    assert page1.status_code == 200
    p1 = page1.json()
    assert len(p1["data"]) == 2
    assert p1["meta"]["has_more"] is True
    cursor = p1["meta"]["cursor"]

    page2 = await client.get(
        f"/api/v1/clients/{fresh_client.id}/plans",
        params={"limit": 2, "cursor": cursor},
    )
    p2 = page2.json()
    assert len(p2["data"]) == 2
    assert p2["meta"]["has_more"] is False

    ids1 = {p["id"] for p in p1["data"]}
    ids2 = {p["id"] for p in p2["data"]}
    assert ids1.isdisjoint(ids2)


async def test_list_plans_empty(client, trainer_and_client, db_session):
    trainer, _ = trainer_and_client
    fresh_client = Client(trainer_id=trainer.id, name="Empty Plan Client")
    db_session.add(fresh_client)
    await db_session.flush()

    response = await client.get(f"/api/v1/clients/{fresh_client.id}/plans")
    assert response.status_code == 200
    assert response.json()["data"] == []


async def test_list_plans_client_not_found_404(client, trainer_and_client):
    response = await client.get(f"/api/v1/clients/{uuid.uuid4()}/plans")
    assert response.status_code == 404


# --- Get Single ---


async def test_get_plan_found(client, trainer_and_client):
    _, db_client = trainer_and_client
    create_resp = await client.post(
        "/api/v1/plans",
        json=_plan(client_id=str(db_client.id), plan_text="Get me"),
    )
    plan_id = create_resp.json()["data"]["id"]

    response = await client.get(f"/api/v1/plans/{plan_id}")
    assert response.status_code == 200
    assert response.json()["data"]["plan_text"] == "Get me"


async def test_get_plan_not_found_404(client, trainer_and_client):
    response = await client.get(f"/api/v1/plans/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_get_plan_wrong_trainer_404(client, trainer_and_client, db_session):
    other_trainer = Trainer(
        email=f"other-plan-{uuid.uuid4().hex[:8]}@test.com", name="Other Plan Trainer",
    )
    db_session.add(other_trainer)
    await db_session.flush()

    other_client = Client(trainer_id=other_trainer.id, name="Other Plan Client")
    db_session.add(other_client)
    await db_session.flush()

    other_plan = SessionPlan(
        trainer_id=other_trainer.id,
        client_id=other_client.id,
        plan_text="Secret plan",
    )
    db_session.add(other_plan)
    await db_session.flush()

    response = await client.get(f"/api/v1/plans/{other_plan.id}")
    assert response.status_code == 404


# --- Update ---


async def test_update_plan_text(client, trainer_and_client):
    _, db_client = trainer_and_client
    create_resp = await client.post(
        "/api/v1/plans",
        json=_plan(client_id=str(db_client.id), plan_text="Original"),
    )
    plan_id = create_resp.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/plans/{plan_id}",
        json={"plan_text": "Updated plan"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["plan_text"] == "Updated plan"


async def test_update_planned_for_date(client, trainer_and_client):
    _, db_client = trainer_and_client
    create_resp = await client.post(
        "/api/v1/plans",
        json=_plan(client_id=str(db_client.id)),
    )
    plan_id = create_resp.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/plans/{plan_id}",
        json={"planned_for_date": "2026-04-01"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["planned_for_date"] == "2026-04-01"


async def test_update_partial_preserves_unchanged(client, trainer_and_client):
    _, db_client = trainer_and_client
    create_resp = await client.post(
        "/api/v1/plans",
        json=_plan(
            client_id=str(db_client.id),
            plan_text="Keep this",
            planned_for_date="2026-03-10",
        ),
    )
    plan_id = create_resp.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/plans/{plan_id}",
        json={"plan_text": "Changed"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["plan_text"] == "Changed"
    assert data["planned_for_date"] == "2026-03-10"


async def test_update_planned_for_date_to_null(client, trainer_and_client):
    """PATCH plan to set planned_for_date to null (un-schedule a plan)."""
    _, db_client = trainer_and_client
    create_resp = await client.post(
        "/api/v1/plans",
        json=_plan(client_id=str(db_client.id), planned_for_date="2026-03-15"),
    )
    plan_id = create_resp.json()["data"]["id"]
    assert create_resp.json()["data"]["planned_for_date"] == "2026-03-15"

    response = await client.patch(
        f"/api/v1/plans/{plan_id}",
        json={"planned_for_date": None},
    )
    assert response.status_code == 200
    assert response.json()["data"]["planned_for_date"] is None
    # plan_text should be unchanged
    assert response.json()["data"]["plan_text"] == "5x5 squats, 3x10 lunges, 3x12 leg press"


async def test_update_empty_plan_text_422(client, trainer_and_client):
    _, db_client = trainer_and_client
    create_resp = await client.post(
        "/api/v1/plans",
        json=_plan(client_id=str(db_client.id)),
    )
    plan_id = create_resp.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/plans/{plan_id}",
        json={"plan_text": ""},
    )
    assert response.status_code == 422


async def test_update_not_found_404(client, trainer_and_client):
    response = await client.patch(
        f"/api/v1/plans/{uuid.uuid4()}",
        json={"plan_text": "Nope"},
    )
    assert response.status_code == 404


# --- Delete ---


async def test_delete_success_204(client, trainer_and_client):
    _, db_client = trainer_and_client
    create_resp = await client.post(
        "/api/v1/plans",
        json=_plan(client_id=str(db_client.id), plan_text="To delete"),
    )
    plan_id = create_resp.json()["data"]["id"]

    response = await client.delete(f"/api/v1/plans/{plan_id}")
    assert response.status_code == 204


async def test_delete_not_found_404(client, trainer_and_client):
    response = await client.delete(f"/api/v1/plans/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_delete_verify_gone(client, trainer_and_client):
    _, db_client = trainer_and_client
    create_resp = await client.post(
        "/api/v1/plans",
        json=_plan(client_id=str(db_client.id), plan_text="Going away"),
    )
    plan_id = create_resp.json()["data"]["id"]

    await client.delete(f"/api/v1/plans/{plan_id}")
    get_resp = await client.get(f"/api/v1/plans/{plan_id}")
    assert get_resp.status_code == 404


async def test_delete_plan_sets_session_plan_id_null(
    client, trainer_and_client, db_session,
):
    """Deleting a plan should SET NULL on sessions referencing it."""
    trainer, db_client = trainer_and_client

    # Create plan via API
    create_resp = await client.post(
        "/api/v1/plans",
        json=_plan(client_id=str(db_client.id), plan_text="Plan for session"),
    )
    plan_id = create_resp.json()["data"]["id"]

    # Create a session that references this plan
    session = Session(
        trainer_id=trainer.id,
        client_id=db_client.id,
        started_at=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
        plan_id=uuid.UUID(plan_id),
    )
    db_session.add(session)
    await db_session.flush()

    # Verify session has plan_id
    session_resp = await client.get(f"/api/v1/sessions/{session.id}")
    assert session_resp.json()["data"]["plan_id"] == plan_id

    # Delete the plan
    await client.delete(f"/api/v1/plans/{plan_id}")

    # Refresh session from DB to see the SET NULL
    await db_session.refresh(session)
    assert session.plan_id is None


# --- Ownership ---


async def test_create_on_wrong_trainers_client_404(
    client, trainer_and_client, db_session,
):
    other_trainer = Trainer(
        email=f"other-pc-{uuid.uuid4().hex[:8]}@test.com", name="Other Trainer PC",
    )
    db_session.add(other_trainer)
    await db_session.flush()

    other_client = Client(trainer_id=other_trainer.id, name="Other Client PC")
    db_session.add(other_client)
    await db_session.flush()

    response = await client.post(
        "/api/v1/plans",
        json=_plan(client_id=str(other_client.id)),
    )
    assert response.status_code == 404


async def test_update_wrong_trainers_plan_404(
    client, trainer_and_client, db_session,
):
    other_trainer = Trainer(
        email=f"other-pu-{uuid.uuid4().hex[:8]}@test.com", name="Other Trainer PU",
    )
    db_session.add(other_trainer)
    await db_session.flush()

    other_client = Client(trainer_id=other_trainer.id, name="Other Client PU")
    db_session.add(other_client)
    await db_session.flush()

    other_plan = SessionPlan(
        trainer_id=other_trainer.id,
        client_id=other_client.id,
        plan_text="Secret",
    )
    db_session.add(other_plan)
    await db_session.flush()

    response = await client.patch(
        f"/api/v1/plans/{other_plan.id}",
        json={"plan_text": "Hacked"},
    )
    assert response.status_code == 404


async def test_delete_wrong_trainers_plan_404(
    client, trainer_and_client, db_session,
):
    other_trainer = Trainer(
        email=f"other-pd-{uuid.uuid4().hex[:8]}@test.com", name="Other Trainer PD",
    )
    db_session.add(other_trainer)
    await db_session.flush()

    other_client = Client(trainer_id=other_trainer.id, name="Other Client PD")
    db_session.add(other_client)
    await db_session.flush()

    other_plan = SessionPlan(
        trainer_id=other_trainer.id,
        client_id=other_client.id,
        plan_text="Secret delete",
    )
    db_session.add(other_plan)
    await db_session.flush()

    response = await client.delete(f"/api/v1/plans/{other_plan.id}")
    assert response.status_code == 404


async def test_list_wrong_trainers_client_404(
    client, trainer_and_client, db_session,
):
    other_trainer = Trainer(
        email=f"other-pl-{uuid.uuid4().hex[:8]}@test.com", name="Other Trainer PL",
    )
    db_session.add(other_trainer)
    await db_session.flush()

    other_client = Client(trainer_id=other_trainer.id, name="Other Client PL")
    db_session.add(other_client)
    await db_session.flush()

    response = await client.get(f"/api/v1/clients/{other_client.id}/plans")
    assert response.status_code == 404
