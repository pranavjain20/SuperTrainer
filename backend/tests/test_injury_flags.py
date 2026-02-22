import uuid
from datetime import datetime, timezone

import pytest

from app.models import Client, InjuryFlag, Session, SessionEntry, Trainer
from app.models import EntryTypeEnum as ETE

pytestmark = pytest.mark.asyncio(loop_scope="session")


# --- Helpers ---


def _flag(client_id, session_id, **overrides):
    base = {
        "client_id": str(client_id),
        "session_id": str(session_id),
        "body_part": "left knee",
        "pain_level": 5,
    }
    base.update(overrides)
    return base


# --- Create ---


async def test_create_flag_happy_path(client, trainer_client_session):
    trainer, db_client, session = trainer_client_session
    payload = _flag(db_client.id, session.id)
    response = await client.post("/api/v1/injury-flags", json=payload)
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["body_part"] == "left knee"
    assert data["pain_level"] == 5
    assert data["client_id"] == str(db_client.id)
    assert data["session_id"] == str(session.id)
    assert data["resolved"] is False
    assert "id" in data


async def test_create_flag_all_fields(client, trainer_client_session):
    _, db_client, session = trainer_client_session
    payload = _flag(
        db_client.id, session.id,
        body_part="right shoulder",
        pain_level=7,
        description="Sharp pain during overhead press",
    )
    response = await client.post("/api/v1/injury-flags", json=payload)
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["body_part"] == "right shoulder"
    assert data["pain_level"] == 7
    assert data["description"] == "Sharp pain during overhead press"


async def test_create_flag_with_session_entry_id(client, trainer_client_session, db_session):
    _, db_client, session = trainer_client_session
    entry = SessionEntry(
        session_id=session.id,
        client_id=db_client.id,
        entry_type=ETE.exercise_card,
        sequence_order=1,
        exercise_name="Overhead Press",
    )
    db_session.add(entry)
    await db_session.flush()

    payload = _flag(
        db_client.id, session.id,
        session_entry_id=str(entry.id),
    )
    response = await client.post("/api/v1/injury-flags", json=payload)
    assert response.status_code == 201
    assert response.json()["data"]["session_entry_id"] == str(entry.id)


async def test_create_flag_client_not_found_404(client, trainer_client_session):
    _, _, session = trainer_client_session
    payload = _flag(uuid.uuid4(), session.id)
    response = await client.post("/api/v1/injury-flags", json=payload)
    assert response.status_code == 404


async def test_create_flag_session_not_found_404(client, trainer_client_session):
    _, db_client, _ = trainer_client_session
    payload = _flag(db_client.id, uuid.uuid4())
    response = await client.post("/api/v1/injury-flags", json=payload)
    assert response.status_code == 404


async def test_create_flag_session_wrong_client_422(client, trainer_client_session, db_session):
    trainer, db_client, _ = trainer_client_session
    other_client = Client(trainer_id=trainer.id, name="Other Flag Client")
    db_session.add(other_client)
    await db_session.flush()

    other_session = Session(
        trainer_id=trainer.id,
        client_id=other_client.id,
        started_at=datetime(2026, 2, 22, 12, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(other_session)
    await db_session.flush()

    # client_id is db_client, but session belongs to other_client
    payload = _flag(db_client.id, other_session.id)
    response = await client.post("/api/v1/injury-flags", json=payload)
    assert response.status_code == 422


async def test_create_flag_entry_wrong_session_422(client, trainer_client_session, db_session):
    trainer, db_client, session = trainer_client_session
    # Create another session for the same client
    other_session = Session(
        trainer_id=trainer.id,
        client_id=db_client.id,
        started_at=datetime(2026, 2, 22, 13, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(other_session)
    await db_session.flush()

    # Entry belongs to other_session
    entry = SessionEntry(
        session_id=other_session.id,
        client_id=db_client.id,
        entry_type=ETE.exercise_card,
        sequence_order=1,
        exercise_name="Squat",
    )
    db_session.add(entry)
    await db_session.flush()

    # Flag references session but entry belongs to other_session
    payload = _flag(db_client.id, session.id, session_entry_id=str(entry.id))
    response = await client.post("/api/v1/injury-flags", json=payload)
    assert response.status_code == 422


async def test_create_flag_pain_level_1_valid(client, trainer_client_session):
    _, db_client, session = trainer_client_session
    payload = _flag(db_client.id, session.id, pain_level=1)
    response = await client.post("/api/v1/injury-flags", json=payload)
    assert response.status_code == 201
    assert response.json()["data"]["pain_level"] == 1


async def test_create_flag_pain_level_10_valid(client, trainer_client_session):
    _, db_client, session = trainer_client_session
    payload = _flag(db_client.id, session.id, pain_level=10)
    response = await client.post("/api/v1/injury-flags", json=payload)
    assert response.status_code == 201
    assert response.json()["data"]["pain_level"] == 10


async def test_create_flag_pain_level_0_422(client, trainer_client_session):
    _, db_client, session = trainer_client_session
    payload = _flag(db_client.id, session.id, pain_level=0)
    response = await client.post("/api/v1/injury-flags", json=payload)
    assert response.status_code == 422


async def test_create_flag_pain_level_11_422(client, trainer_client_session):
    _, db_client, session = trainer_client_session
    payload = _flag(db_client.id, session.id, pain_level=11)
    response = await client.post("/api/v1/injury-flags", json=payload)
    assert response.status_code == 422


# --- List by Client ---


async def test_list_flags_returns_flags(client, trainer_client_session):
    _, db_client, session = trainer_client_session
    for part in ["knee", "shoulder", "back"]:
        await client.post(
            "/api/v1/injury-flags",
            json=_flag(db_client.id, session.id, body_part=part),
        )

    response = await client.get(f"/api/v1/clients/{db_client.id}/injury-flags")
    assert response.status_code == 200
    assert len(response.json()["data"]) >= 3


async def test_list_flags_ordered_by_flagged_at_desc(client, trainer_client_session, db_session):
    trainer, _, _ = trainer_client_session
    fresh_client = Client(trainer_id=trainer.id, name="Flag Order Client")
    db_session.add(fresh_client)
    await db_session.flush()

    fresh_session = Session(
        trainer_id=trainer.id,
        client_id=fresh_client.id,
        started_at=datetime(2026, 2, 22, 14, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(fresh_session)
    await db_session.flush()

    for part in ["first", "second", "third"]:
        await client.post(
            "/api/v1/injury-flags",
            json=_flag(fresh_client.id, fresh_session.id, body_part=part),
        )

    response = await client.get(f"/api/v1/clients/{fresh_client.id}/injury-flags")
    data = response.json()["data"]
    assert data[0]["body_part"] == "third"


async def test_list_flags_pagination(client, trainer_client_session, db_session):
    trainer, _, _ = trainer_client_session
    fresh_client = Client(trainer_id=trainer.id, name="Flag Page Client")
    db_session.add(fresh_client)
    await db_session.flush()

    fresh_session = Session(
        trainer_id=trainer.id,
        client_id=fresh_client.id,
        started_at=datetime(2026, 2, 22, 15, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(fresh_session)
    await db_session.flush()

    for i in range(4):
        await client.post(
            "/api/v1/injury-flags",
            json=_flag(fresh_client.id, fresh_session.id, body_part=f"part-{i}"),
        )

    page1 = await client.get(
        f"/api/v1/clients/{fresh_client.id}/injury-flags",
        params={"limit": 2},
    )
    assert page1.status_code == 200
    p1 = page1.json()
    assert len(p1["data"]) == 2
    assert p1["meta"]["has_more"] is True
    cursor = p1["meta"]["cursor"]

    page2 = await client.get(
        f"/api/v1/clients/{fresh_client.id}/injury-flags",
        params={"limit": 2, "cursor": cursor},
    )
    p2 = page2.json()
    assert len(p2["data"]) == 2
    assert p2["meta"]["has_more"] is False

    ids1 = {f["id"] for f in p1["data"]}
    ids2 = {f["id"] for f in p2["data"]}
    assert ids1.isdisjoint(ids2)


async def test_list_flags_empty(client, trainer_client_session, db_session):
    trainer, _, _ = trainer_client_session
    fresh_client = Client(trainer_id=trainer.id, name="Empty Flag Client")
    db_session.add(fresh_client)
    await db_session.flush()

    response = await client.get(f"/api/v1/clients/{fresh_client.id}/injury-flags")
    assert response.status_code == 200
    assert response.json()["data"] == []


async def test_list_flags_client_not_found_404(client, trainer_client_session):
    response = await client.get(f"/api/v1/clients/{uuid.uuid4()}/injury-flags")
    assert response.status_code == 404


# --- Get Single ---


async def test_get_flag_found(client, trainer_client_session):
    _, db_client, session = trainer_client_session
    create_resp = await client.post(
        "/api/v1/injury-flags",
        json=_flag(db_client.id, session.id, body_part="get me"),
    )
    flag_id = create_resp.json()["data"]["id"]

    response = await client.get(f"/api/v1/injury-flags/{flag_id}")
    assert response.status_code == 200
    assert response.json()["data"]["body_part"] == "get me"


async def test_get_flag_not_found_404(client, trainer_client_session):
    response = await client.get(f"/api/v1/injury-flags/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_get_flag_wrong_trainer_404(client, trainer_client_session, db_session):
    other_trainer = Trainer(
        email=f"other-fg-{uuid.uuid4().hex[:8]}@test.com", name="Other Flag Trainer",
    )
    db_session.add(other_trainer)
    await db_session.flush()

    other_client = Client(trainer_id=other_trainer.id, name="Other Flag Client")
    db_session.add(other_client)
    await db_session.flush()

    other_session = Session(
        trainer_id=other_trainer.id,
        client_id=other_client.id,
        started_at=datetime(2026, 2, 22, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(other_session)
    await db_session.flush()

    other_flag = InjuryFlag(
        client_id=other_client.id,
        session_id=other_session.id,
        body_part="secret knee",
        pain_level=3,
    )
    db_session.add(other_flag)
    await db_session.flush()

    response = await client.get(f"/api/v1/injury-flags/{other_flag.id}")
    assert response.status_code == 404


# --- Update ---


async def test_update_body_part(client, trainer_client_session):
    _, db_client, session = trainer_client_session
    create_resp = await client.post(
        "/api/v1/injury-flags",
        json=_flag(db_client.id, session.id, body_part="left knee"),
    )
    flag_id = create_resp.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/injury-flags/{flag_id}",
        json={"body_part": "right knee"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["body_part"] == "right knee"


async def test_update_pain_level(client, trainer_client_session):
    _, db_client, session = trainer_client_session
    create_resp = await client.post(
        "/api/v1/injury-flags",
        json=_flag(db_client.id, session.id, pain_level=5),
    )
    flag_id = create_resp.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/injury-flags/{flag_id}",
        json={"pain_level": 8},
    )
    assert response.status_code == 200
    assert response.json()["data"]["pain_level"] == 8


async def test_update_description(client, trainer_client_session):
    _, db_client, session = trainer_client_session
    create_resp = await client.post(
        "/api/v1/injury-flags",
        json=_flag(db_client.id, session.id),
    )
    flag_id = create_resp.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/injury-flags/{flag_id}",
        json={"description": "Getting worse with heavy loads"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["description"] == "Getting worse with heavy loads"


async def test_update_resolved(client, trainer_client_session):
    _, db_client, session = trainer_client_session
    create_resp = await client.post(
        "/api/v1/injury-flags",
        json=_flag(db_client.id, session.id),
    )
    flag_id = create_resp.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/injury-flags/{flag_id}",
        json={"resolved": True, "resolved_at": "2026-03-01T10:00:00Z"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["resolved"] is True
    assert data["resolved_at"] is not None


async def test_update_partial_preserves_unchanged(client, trainer_client_session):
    _, db_client, session = trainer_client_session
    create_resp = await client.post(
        "/api/v1/injury-flags",
        json=_flag(
            db_client.id, session.id,
            body_part="lower back",
            pain_level=6,
            description="Dull ache",
        ),
    )
    flag_id = create_resp.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/injury-flags/{flag_id}",
        json={"pain_level": 3},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["pain_level"] == 3
    assert data["body_part"] == "lower back"
    assert data["description"] == "Dull ache"


async def test_update_resolved_at_without_resolved_422(client, trainer_client_session):
    """PATCH with resolved_at but without resolved=true should fail validation."""
    _, db_client, session = trainer_client_session
    create_resp = await client.post(
        "/api/v1/injury-flags",
        json=_flag(db_client.id, session.id),
    )
    flag_id = create_resp.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/injury-flags/{flag_id}",
        json={"resolved_at": "2026-03-01T10:00:00Z"},
    )
    assert response.status_code == 422


async def test_update_resolved_at_with_resolved_false_422(client, trainer_client_session):
    """PATCH with resolved_at + resolved=false should fail validation."""
    _, db_client, session = trainer_client_session
    create_resp = await client.post(
        "/api/v1/injury-flags",
        json=_flag(db_client.id, session.id),
    )
    flag_id = create_resp.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/injury-flags/{flag_id}",
        json={"resolved": False, "resolved_at": "2026-03-01T10:00:00Z"},
    )
    assert response.status_code == 422


async def test_update_pain_level_0_422(client, trainer_client_session):
    _, db_client, session = trainer_client_session
    create_resp = await client.post(
        "/api/v1/injury-flags",
        json=_flag(db_client.id, session.id),
    )
    flag_id = create_resp.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/injury-flags/{flag_id}",
        json={"pain_level": 0},
    )
    assert response.status_code == 422


async def test_update_not_found_404(client, trainer_client_session):
    response = await client.patch(
        f"/api/v1/injury-flags/{uuid.uuid4()}",
        json={"body_part": "nope"},
    )
    assert response.status_code == 404


# --- Delete ---


async def test_delete_success_204(client, trainer_client_session):
    _, db_client, session = trainer_client_session
    create_resp = await client.post(
        "/api/v1/injury-flags",
        json=_flag(db_client.id, session.id, body_part="to delete"),
    )
    flag_id = create_resp.json()["data"]["id"]

    response = await client.delete(f"/api/v1/injury-flags/{flag_id}")
    assert response.status_code == 204


async def test_delete_not_found_404(client, trainer_client_session):
    response = await client.delete(f"/api/v1/injury-flags/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_delete_verify_gone(client, trainer_client_session):
    _, db_client, session = trainer_client_session
    create_resp = await client.post(
        "/api/v1/injury-flags",
        json=_flag(db_client.id, session.id, body_part="going away"),
    )
    flag_id = create_resp.json()["data"]["id"]

    await client.delete(f"/api/v1/injury-flags/{flag_id}")
    get_resp = await client.get(f"/api/v1/injury-flags/{flag_id}")
    assert get_resp.status_code == 404


async def test_delete_doesnt_affect_other_flags(client, trainer_client_session):
    _, db_client, session = trainer_client_session
    resp1 = await client.post(
        "/api/v1/injury-flags",
        json=_flag(db_client.id, session.id, body_part="keep me"),
    )
    resp2 = await client.post(
        "/api/v1/injury-flags",
        json=_flag(db_client.id, session.id, body_part="delete me"),
    )
    keep_id = resp1.json()["data"]["id"]
    delete_id = resp2.json()["data"]["id"]

    await client.delete(f"/api/v1/injury-flags/{delete_id}")

    get_resp = await client.get(f"/api/v1/injury-flags/{keep_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["body_part"] == "keep me"


# --- Cascade + Ownership ---


async def test_session_delete_cascades_flags(client, trainer_client_session, db_session):
    trainer, db_client, _ = trainer_client_session
    cascade_session = Session(
        trainer_id=trainer.id,
        client_id=db_client.id,
        started_at=datetime(2026, 2, 23, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(cascade_session)
    await db_session.flush()

    resp = await client.post(
        "/api/v1/injury-flags",
        json=_flag(db_client.id, cascade_session.id, body_part="will cascade"),
    )
    flag_id = resp.json()["data"]["id"]

    await client.delete(f"/api/v1/sessions/{cascade_session.id}")

    get_resp = await client.get(f"/api/v1/injury-flags/{flag_id}")
    assert get_resp.status_code == 404


async def test_client_delete_cascades_flags(client, trainer_client_session, db_session):
    trainer, _, _ = trainer_client_session
    cascade_client = Client(trainer_id=trainer.id, name="Cascade Flag Client")
    db_session.add(cascade_client)
    await db_session.flush()

    cascade_session = Session(
        trainer_id=trainer.id,
        client_id=cascade_client.id,
        started_at=datetime(2026, 2, 23, 11, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(cascade_session)
    await db_session.flush()

    resp = await client.post(
        "/api/v1/injury-flags",
        json=_flag(cascade_client.id, cascade_session.id, body_part="will cascade"),
    )
    flag_id = resp.json()["data"]["id"]

    # Delete client directly — no DELETE /clients endpoint exists yet
    await db_session.delete(cascade_client)
    await db_session.commit()

    get_resp = await client.get(f"/api/v1/injury-flags/{flag_id}")
    assert get_resp.status_code == 404


async def test_create_flag_wrong_trainers_client_404(
    client, trainer_client_session, db_session,
):
    other_trainer = Trainer(
        email=f"other-fc-{uuid.uuid4().hex[:8]}@test.com", name="Other FC Trainer",
    )
    db_session.add(other_trainer)
    await db_session.flush()

    other_client = Client(trainer_id=other_trainer.id, name="Other FC Client")
    db_session.add(other_client)
    await db_session.flush()

    other_session = Session(
        trainer_id=other_trainer.id,
        client_id=other_client.id,
        started_at=datetime(2026, 2, 22, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(other_session)
    await db_session.flush()

    payload = _flag(other_client.id, other_session.id)
    response = await client.post("/api/v1/injury-flags", json=payload)
    assert response.status_code == 404


async def test_get_wrong_trainers_flag_404(
    client, trainer_client_session, db_session,
):
    other_trainer = Trainer(
        email=f"other-fgg-{uuid.uuid4().hex[:8]}@test.com", name="Other FGG Trainer",
    )
    db_session.add(other_trainer)
    await db_session.flush()

    other_client = Client(trainer_id=other_trainer.id, name="Other FGG Client")
    db_session.add(other_client)
    await db_session.flush()

    other_session = Session(
        trainer_id=other_trainer.id,
        client_id=other_client.id,
        started_at=datetime(2026, 2, 22, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(other_session)
    await db_session.flush()

    flag = InjuryFlag(
        client_id=other_client.id,
        session_id=other_session.id,
        body_part="secret",
        pain_level=3,
    )
    db_session.add(flag)
    await db_session.flush()

    response = await client.get(f"/api/v1/injury-flags/{flag.id}")
    assert response.status_code == 404


async def test_delete_wrong_trainers_flag_404(
    client, trainer_client_session, db_session,
):
    other_trainer = Trainer(
        email=f"other-fd-{uuid.uuid4().hex[:8]}@test.com", name="Other FD Trainer",
    )
    db_session.add(other_trainer)
    await db_session.flush()

    other_client = Client(trainer_id=other_trainer.id, name="Other FD Client")
    db_session.add(other_client)
    await db_session.flush()

    other_session = Session(
        trainer_id=other_trainer.id,
        client_id=other_client.id,
        started_at=datetime(2026, 2, 22, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(other_session)
    await db_session.flush()

    flag = InjuryFlag(
        client_id=other_client.id,
        session_id=other_session.id,
        body_part="secret del",
        pain_level=4,
    )
    db_session.add(flag)
    await db_session.flush()

    response = await client.delete(f"/api/v1/injury-flags/{flag.id}")
    assert response.status_code == 404


async def test_update_wrong_trainers_flag_404(
    client, trainer_client_session, db_session,
):
    other_trainer = Trainer(
        email=f"other-fu-{uuid.uuid4().hex[:8]}@test.com", name="Other FU Trainer",
    )
    db_session.add(other_trainer)
    await db_session.flush()

    other_client = Client(trainer_id=other_trainer.id, name="Other FU Client")
    db_session.add(other_client)
    await db_session.flush()

    other_session = Session(
        trainer_id=other_trainer.id,
        client_id=other_client.id,
        started_at=datetime(2026, 2, 22, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(other_session)
    await db_session.flush()

    flag = InjuryFlag(
        client_id=other_client.id,
        session_id=other_session.id,
        body_part="secret upd",
        pain_level=5,
    )
    db_session.add(flag)
    await db_session.flush()

    response = await client.patch(
        f"/api/v1/injury-flags/{flag.id}",
        json={"pain_level": 9},
    )
    assert response.status_code == 404


async def test_list_wrong_trainers_client_flags_404(
    client, trainer_client_session, db_session,
):
    other_trainer = Trainer(
        email=f"other-fl-{uuid.uuid4().hex[:8]}@test.com", name="Other FL Trainer",
    )
    db_session.add(other_trainer)
    await db_session.flush()

    other_client = Client(trainer_id=other_trainer.id, name="Other FL Client")
    db_session.add(other_client)
    await db_session.flush()

    response = await client.get(f"/api/v1/clients/{other_client.id}/injury-flags")
    assert response.status_code == 404
