import uuid
from datetime import datetime, timezone

import pytest

from app.models import Client, Session, Trainer

pytestmark = pytest.mark.asyncio(loop_scope="session")


# --- Helpers ---


def _exercise_card(**overrides):
    """Build an exercise_card payload. Overrides replace defaults."""
    base = {
        "entry_type": "exercise_card",
        "exercise_name": "Bench Press",
    }
    base.update(overrides)
    return base


def _observation_card(**overrides):
    """Build an observation_card payload. Overrides replace defaults."""
    base = {
        "entry_type": "observation_card",
        "observation_text": "Client seemed tired today",
    }
    base.update(overrides)
    return base


# --- Create Entry ---


async def test_create_exercise_card_happy_path(client, trainer_client_session):
    _, _, session = trainer_client_session
    response = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json=_exercise_card(),
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["entry_type"] == "exercise_card"
    assert data["exercise_name"] == "Bench Press"
    assert data["session_id"] == str(session.id)
    assert data["sequence_order"] == 1
    assert data["observation_text"] is None
    assert "id" in data


async def test_create_observation_card_happy_path(client, trainer_client_session):
    _, _, session = trainer_client_session
    response = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json=_observation_card(),
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["entry_type"] == "observation_card"
    assert data["observation_text"] == "Client seemed tired today"
    assert data["exercise_name"] is None
    assert data["sets"] is None


async def test_create_exercise_card_all_fields(client, trainer_client_session):
    _, _, session = trainer_client_session
    payload = _exercise_card(
        sets=[
            {"set_number": 1, "weight_kg": 80, "reps": 8, "rpe": 7},
            {"set_number": 2, "weight_kg": 85, "reps": 6, "rpe": 8.5},
        ],
        total_volume_kg=1150.0,
        exercise_canonical="barbell_bench_press",
        form_notes=["Good depth", "Slight elbow flare on set 2"],
        cues_given=["Drive through heels", "Keep chest up"],
        cue_effectiveness={"Drive through heels": "effective", "Keep chest up": "needs_work"},
        performed_at="2026-02-22T10:15:00Z",
    )
    response = await client.post(
        f"/api/v1/sessions/{session.id}/entries", json=payload,
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert len(data["sets"]) == 2
    assert data["sets"][0]["weight_kg"] == 80
    assert data["total_volume_kg"] == 1150.0
    assert data["exercise_canonical"] == "barbell_bench_press"
    assert len(data["form_notes"]) == 2
    assert len(data["cues_given"]) == 2
    assert data["cue_effectiveness"]["Drive through heels"] == "effective"
    assert data["performed_at"] is not None


async def test_create_observation_card_all_fields(client, trainer_client_session):
    _, _, session = trainer_client_session
    payload = _observation_card(
        flag_color="red",
        flag_reason="pain reported",
        attached_to_set=3,
        performed_at="2026-02-22T10:20:00Z",
    )
    response = await client.post(
        f"/api/v1/sessions/{session.id}/entries", json=payload,
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["flag_color"] == "red"
    assert data["flag_reason"] == "pain reported"
    assert data["attached_to_set"] == 3


async def test_create_auto_sequence_order(client, trainer_client_session, db_session):
    """Create 3 entries without sequence_order — should auto-assign 1, 2, 3 sequentially."""
    # Create a fresh session for clean sequencing
    trainer, db_client, _ = trainer_client_session
    fresh_session = Session(
        trainer_id=trainer.id,
        client_id=db_client.id,
        started_at=datetime(2026, 2, 22, 14, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(fresh_session)
    await db_session.flush()

    orders = []
    for name in ["Squat", "Deadlift", "Leg Press"]:
        resp = await client.post(
            f"/api/v1/sessions/{fresh_session.id}/entries",
            json=_exercise_card(exercise_name=name),
        )
        assert resp.status_code == 201
        orders.append(resp.json()["data"]["sequence_order"])

    assert orders == [1, 2, 3]


async def test_create_explicit_sequence_order(client, trainer_client_session, db_session):
    trainer, db_client, _ = trainer_client_session
    fresh_session = Session(
        trainer_id=trainer.id,
        client_id=db_client.id,
        started_at=datetime(2026, 2, 22, 15, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(fresh_session)
    await db_session.flush()

    response = await client.post(
        f"/api/v1/sessions/{fresh_session.id}/entries",
        json=_exercise_card(sequence_order=5),
    )
    assert response.status_code == 201
    assert response.json()["data"]["sequence_order"] == 5


async def test_create_exercise_card_empty_sets_array(client, trainer_client_session):
    """POST entry with sets=[] should succeed (exercise with no recorded sets yet)."""
    _, _, session = trainer_client_session
    response = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json=_exercise_card(sets=[]),
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["sets"] == []
    assert data["exercise_name"] == "Bench Press"


async def test_create_missing_exercise_name_422(client, trainer_client_session):
    _, _, session = trainer_client_session
    response = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json={"entry_type": "exercise_card"},
    )
    assert response.status_code == 422


async def test_create_missing_observation_text_422(client, trainer_client_session):
    _, _, session = trainer_client_session
    response = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json={"entry_type": "observation_card"},
    )
    assert response.status_code == 422


async def test_create_observation_text_on_exercise_card_422(client, trainer_client_session):
    _, _, session = trainer_client_session
    response = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json=_exercise_card(observation_text="should fail"),
    )
    assert response.status_code == 422


async def test_create_exercise_name_on_observation_card_422(client, trainer_client_session):
    _, _, session = trainer_client_session
    response = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json=_observation_card(exercise_name="should fail"),
    )
    assert response.status_code == 422


async def test_create_sets_on_observation_card_422(client, trainer_client_session):
    _, _, session = trainer_client_session
    response = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json=_observation_card(sets=[{"set": 1}]),
    )
    assert response.status_code == 422


async def test_create_invalid_entry_type_422(client, trainer_client_session):
    _, _, session = trainer_client_session
    response = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json={"entry_type": "bogus", "exercise_name": "Squat"},
    )
    assert response.status_code == 422


async def test_create_session_not_found_404(client, trainer_client_session):
    response = await client.post(
        f"/api/v1/sessions/{uuid.uuid4()}/entries",
        json=_exercise_card(),
    )
    assert response.status_code == 404


async def test_create_realistic_sets_jsonb_roundtrip(client, trainer_client_session):
    _, _, session = trainer_client_session
    sets_data = [
        {"set_number": 1, "weight_kg": 100, "reps": 5, "rpe": 7, "rest_seconds": 180},
        {"set_number": 2, "weight_kg": 100, "reps": 5, "rpe": 7.5, "rest_seconds": 180},
        {"set_number": 3, "weight_kg": 100, "reps": 4, "rpe": 9, "notes": "grip slipped"},
    ]
    response = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json=_exercise_card(sets=sets_data, total_volume_kg=1400.0),
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert len(data["sets"]) == 3
    assert data["sets"][2]["notes"] == "grip slipped"
    assert data["sets"][0]["rest_seconds"] == 180


# --- List by Session ---


async def test_list_by_session_ordered(client, trainer_client_session, db_session):
    trainer, db_client, _ = trainer_client_session
    fresh_session = Session(
        trainer_id=trainer.id,
        client_id=db_client.id,
        started_at=datetime(2026, 2, 22, 16, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(fresh_session)
    await db_session.flush()

    for i, name in enumerate(["Squat", "Bench Press", "Deadlift"], 1):
        await client.post(
            f"/api/v1/sessions/{fresh_session.id}/entries",
            json=_exercise_card(exercise_name=name, sequence_order=i),
        )

    response = await client.get(f"/api/v1/sessions/{fresh_session.id}/entries")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 3
    names = [e["exercise_name"] for e in data]
    assert names == ["Squat", "Bench Press", "Deadlift"]
    orders = [e["sequence_order"] for e in data]
    assert orders == [1, 2, 3]


async def test_list_by_session_empty(client, trainer_client_session, db_session):
    trainer, db_client, _ = trainer_client_session
    empty_session = Session(
        trainer_id=trainer.id,
        client_id=db_client.id,
        started_at=datetime(2026, 2, 22, 17, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(empty_session)
    await db_session.flush()

    response = await client.get(f"/api/v1/sessions/{empty_session.id}/entries")
    assert response.status_code == 200
    assert response.json()["data"] == []
    assert response.json()["meta"]["has_more"] is False


async def test_list_by_session_not_found_404(client, trainer_client_session):
    response = await client.get(f"/api/v1/sessions/{uuid.uuid4()}/entries")
    assert response.status_code == 404


async def test_list_by_session_mixed_types(client, trainer_client_session, db_session):
    trainer, db_client, _ = trainer_client_session
    fresh_session = Session(
        trainer_id=trainer.id,
        client_id=db_client.id,
        started_at=datetime(2026, 2, 22, 18, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(fresh_session)
    await db_session.flush()

    await client.post(
        f"/api/v1/sessions/{fresh_session.id}/entries",
        json=_exercise_card(exercise_name="Squat", sequence_order=1),
    )
    await client.post(
        f"/api/v1/sessions/{fresh_session.id}/entries",
        json=_observation_card(sequence_order=2),
    )
    await client.post(
        f"/api/v1/sessions/{fresh_session.id}/entries",
        json=_exercise_card(exercise_name="Deadlift", sequence_order=3),
    )

    response = await client.get(f"/api/v1/sessions/{fresh_session.id}/entries")
    data = response.json()["data"]
    assert len(data) == 3
    types = [e["entry_type"] for e in data]
    assert types == ["exercise_card", "observation_card", "exercise_card"]


async def test_list_by_session_excludes_other_sessions(
    client, trainer_client_session, db_session,
):
    trainer, db_client, _ = trainer_client_session
    session_a = Session(
        trainer_id=trainer.id, client_id=db_client.id,
        started_at=datetime(2026, 2, 22, 19, 0, 0, tzinfo=timezone.utc),
    )
    session_b = Session(
        trainer_id=trainer.id, client_id=db_client.id,
        started_at=datetime(2026, 2, 22, 20, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add_all([session_a, session_b])
    await db_session.flush()

    await client.post(
        f"/api/v1/sessions/{session_a.id}/entries",
        json=_exercise_card(exercise_name="Squat"),
    )
    await client.post(
        f"/api/v1/sessions/{session_b.id}/entries",
        json=_exercise_card(exercise_name="Deadlift"),
    )

    resp_a = await client.get(f"/api/v1/sessions/{session_a.id}/entries")
    data_a = resp_a.json()["data"]
    assert len(data_a) == 1
    assert data_a[0]["exercise_name"] == "Squat"


async def test_list_by_session_no_pagination(client, trainer_client_session, db_session):
    trainer, db_client, _ = trainer_client_session
    fresh_session = Session(
        trainer_id=trainer.id, client_id=db_client.id,
        started_at=datetime(2026, 2, 22, 21, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(fresh_session)
    await db_session.flush()

    for i in range(5):
        await client.post(
            f"/api/v1/sessions/{fresh_session.id}/entries",
            json=_exercise_card(exercise_name=f"Exercise {i}"),
        )

    response = await client.get(f"/api/v1/sessions/{fresh_session.id}/entries")
    assert response.json()["meta"]["has_more"] is False
    assert len(response.json()["data"]) == 5


# --- List by Client ---


async def test_list_by_client_across_sessions(client, trainer_client_session, db_session):
    trainer, db_client, _ = trainer_client_session
    s1 = Session(
        trainer_id=trainer.id, client_id=db_client.id,
        started_at=datetime(2026, 2, 21, 10, 0, 0, tzinfo=timezone.utc),
    )
    s2 = Session(
        trainer_id=trainer.id, client_id=db_client.id,
        started_at=datetime(2026, 2, 22, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add_all([s1, s2])
    await db_session.flush()

    await client.post(
        f"/api/v1/sessions/{s1.id}/entries",
        json=_exercise_card(exercise_name="Squat"),
    )
    await client.post(
        f"/api/v1/sessions/{s2.id}/entries",
        json=_exercise_card(exercise_name="Deadlift"),
    )

    response = await client.get(f"/api/v1/clients/{db_client.id}/entries")
    assert response.status_code == 200
    data = response.json()["data"]
    # Should have at least the 2 we just created
    names = [e["exercise_name"] for e in data]
    assert "Squat" in names
    assert "Deadlift" in names


async def test_list_by_client_ordered_by_created_at_desc(
    client, trainer_client_session, db_session,
):
    trainer, db_client, _ = trainer_client_session
    fresh_client = Client(trainer_id=trainer.id, name="Order Test Client")
    db_session.add(fresh_client)
    await db_session.flush()

    s = Session(
        trainer_id=trainer.id, client_id=fresh_client.id,
        started_at=datetime(2026, 2, 22, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(s)
    await db_session.flush()

    for name in ["First", "Second", "Third"]:
        await client.post(
            f"/api/v1/sessions/{s.id}/entries",
            json=_exercise_card(exercise_name=name),
        )

    response = await client.get(f"/api/v1/clients/{fresh_client.id}/entries")
    data = response.json()["data"]
    assert len(data) == 3
    # created_at desc: last created first
    assert data[0]["exercise_name"] == "Third"


async def test_list_by_client_pagination(client, trainer_client_session, db_session):
    trainer, _, _ = trainer_client_session
    fresh_client = Client(trainer_id=trainer.id, name="Pagination Test Client")
    db_session.add(fresh_client)
    await db_session.flush()

    s = Session(
        trainer_id=trainer.id, client_id=fresh_client.id,
        started_at=datetime(2026, 2, 22, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(s)
    await db_session.flush()

    for i in range(4):
        await client.post(
            f"/api/v1/sessions/{s.id}/entries",
            json=_exercise_card(exercise_name=f"Ex{i}"),
        )

    page1 = await client.get(
        f"/api/v1/clients/{fresh_client.id}/entries", params={"limit": 2},
    )
    assert page1.status_code == 200
    p1 = page1.json()
    assert len(p1["data"]) == 2
    assert p1["meta"]["has_more"] is True
    cursor = p1["meta"]["cursor"]

    page2 = await client.get(
        f"/api/v1/clients/{fresh_client.id}/entries",
        params={"limit": 2, "cursor": cursor},
    )
    assert page2.status_code == 200
    p2 = page2.json()
    assert len(p2["data"]) == 2
    assert p2["meta"]["has_more"] is False

    # No overlap
    ids1 = {e["id"] for e in p1["data"]}
    ids2 = {e["id"] for e in p2["data"]}
    assert ids1.isdisjoint(ids2)


async def test_list_by_client_empty(client, trainer_client_session, db_session):
    trainer, _, _ = trainer_client_session
    fresh_client = Client(trainer_id=trainer.id, name="Empty Client")
    db_session.add(fresh_client)
    await db_session.flush()

    response = await client.get(f"/api/v1/clients/{fresh_client.id}/entries")
    assert response.status_code == 200
    assert response.json()["data"] == []


async def test_list_by_client_not_found_404(client, trainer_client_session):
    response = await client.get(f"/api/v1/clients/{uuid.uuid4()}/entries")
    assert response.status_code == 404


async def test_list_by_client_excludes_other_clients(
    client, trainer_client_session, db_session,
):
    trainer, _, _ = trainer_client_session
    client_a = Client(trainer_id=trainer.id, name="Client A")
    client_b = Client(trainer_id=trainer.id, name="Client B")
    db_session.add_all([client_a, client_b])
    await db_session.flush()

    s_a = Session(
        trainer_id=trainer.id, client_id=client_a.id,
        started_at=datetime(2026, 2, 22, 10, 0, 0, tzinfo=timezone.utc),
    )
    s_b = Session(
        trainer_id=trainer.id, client_id=client_b.id,
        started_at=datetime(2026, 2, 22, 11, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add_all([s_a, s_b])
    await db_session.flush()

    await client.post(
        f"/api/v1/sessions/{s_a.id}/entries",
        json=_exercise_card(exercise_name="Squat"),
    )
    await client.post(
        f"/api/v1/sessions/{s_b.id}/entries",
        json=_exercise_card(exercise_name="Deadlift"),
    )

    resp = await client.get(f"/api/v1/clients/{client_a.id}/entries")
    data = resp.json()["data"]
    assert all(e["client_id"] == str(client_a.id) for e in data)


async def test_list_by_client_entries_from_multiple_sessions(
    client, trainer_client_session, db_session,
):
    trainer, _, _ = trainer_client_session
    multi_client = Client(trainer_id=trainer.id, name="Multi Session Client")
    db_session.add(multi_client)
    await db_session.flush()

    s1 = Session(
        trainer_id=trainer.id, client_id=multi_client.id,
        started_at=datetime(2026, 2, 20, 10, 0, 0, tzinfo=timezone.utc),
    )
    s2 = Session(
        trainer_id=trainer.id, client_id=multi_client.id,
        started_at=datetime(2026, 2, 21, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add_all([s1, s2])
    await db_session.flush()

    await client.post(
        f"/api/v1/sessions/{s1.id}/entries",
        json=_exercise_card(exercise_name="Squat"),
    )
    await client.post(
        f"/api/v1/sessions/{s2.id}/entries",
        json=_exercise_card(exercise_name="Deadlift"),
    )

    resp = await client.get(f"/api/v1/clients/{multi_client.id}/entries")
    data = resp.json()["data"]
    session_ids = {e["session_id"] for e in data}
    assert len(session_ids) == 2


# --- Get Single ---


async def test_get_entry_found(client, trainer_client_session):
    _, _, session = trainer_client_session
    create_resp = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json=_exercise_card(
            exercise_name="Overhead Press",
            sets=[{"set_number": 1, "weight_kg": 50, "reps": 10}],
        ),
    )
    entry_id = create_resp.json()["data"]["id"]

    response = await client.get(f"/api/v1/entries/{entry_id}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == entry_id
    assert data["exercise_name"] == "Overhead Press"
    assert len(data["sets"]) == 1


async def test_get_entry_not_found_404(client, trainer_client_session):
    response = await client.get(f"/api/v1/entries/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_get_exercise_card_has_null_observation_fields(client, trainer_client_session):
    _, _, session = trainer_client_session
    create_resp = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json=_exercise_card(),
    )
    entry_id = create_resp.json()["data"]["id"]

    response = await client.get(f"/api/v1/entries/{entry_id}")
    data = response.json()["data"]
    assert data["observation_text"] is None
    assert data["attached_to_set"] is None
    assert data["flag_color"] is None
    assert data["flag_reason"] is None


# --- Update ---


async def test_update_exercise_name(client, trainer_client_session):
    _, _, session = trainer_client_session
    create_resp = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json=_exercise_card(exercise_name="Squat"),
    )
    entry_id = create_resp.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/entries/{entry_id}",
        json={"exercise_name": "Back Squat"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["exercise_name"] == "Back Squat"


async def test_update_observation_text(client, trainer_client_session):
    _, _, session = trainer_client_session
    create_resp = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json=_observation_card(),
    )
    entry_id = create_resp.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/entries/{entry_id}",
        json={"observation_text": "Updated observation"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["observation_text"] == "Updated observation"


async def test_update_sets_jsonb(client, trainer_client_session):
    _, _, session = trainer_client_session
    create_resp = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json=_exercise_card(sets=[{"set_number": 1, "weight_kg": 80, "reps": 8}]),
    )
    entry_id = create_resp.json()["data"]["id"]

    new_sets = [
        {"set_number": 1, "weight_kg": 80, "reps": 8},
        {"set_number": 2, "weight_kg": 85, "reps": 6},
    ]
    response = await client.patch(
        f"/api/v1/entries/{entry_id}",
        json={"sets": new_sets},
    )
    assert response.status_code == 200
    assert len(response.json()["data"]["sets"]) == 2


async def test_update_sets_recalculates_total_volume_kg(client, trainer_client_session):
    """total_volume_kg must be recalculated when sets change via inline edit."""
    _, _, session = trainer_client_session
    create_resp = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json=_exercise_card(
            sets=[{"reps": 10, "weight": 80, "weight_unit": "kg"}],
            total_volume_kg=800.0,
        ),
    )
    entry_id = create_resp.json()["data"]["id"]
    assert create_resp.json()["data"]["total_volume_kg"] == 800.0

    # Change weight from 80 to 90 via inline edit
    response = await client.patch(
        f"/api/v1/entries/{entry_id}",
        json={"sets": [{"reps": 10, "weight": 90, "weight_unit": "kg"}]},
    )
    assert response.status_code == 200
    assert response.json()["data"]["total_volume_kg"] == 900.0


async def test_update_sets_recalculates_with_weight_kg_format(client, trainer_client_session):
    """total_volume_kg recalculation handles seed data format (weight_kg)."""
    _, _, session = trainer_client_session
    create_resp = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json=_exercise_card(
            sets=[{"reps": 8, "weight_kg": 60}],
            total_volume_kg=480.0,
        ),
    )
    entry_id = create_resp.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/entries/{entry_id}",
        json={"sets": [{"reps": 8, "weight_kg": 70}]},
    )
    assert response.status_code == 200
    assert response.json()["data"]["total_volume_kg"] == 560.0


async def test_update_sets_no_weight_clears_total_volume(client, trainer_client_session):
    """Bodyweight exercises (no weight field) should have total_volume_kg = None."""
    _, _, session = trainer_client_session
    create_resp = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json=_exercise_card(
            sets=[{"reps": 10, "weight": 80, "weight_unit": "kg"}],
            total_volume_kg=800.0,
        ),
    )
    entry_id = create_resp.json()["data"]["id"]

    # Edit to remove weight (bodyweight exercise)
    response = await client.patch(
        f"/api/v1/entries/{entry_id}",
        json={"sets": [{"reps": 10}]},
    )
    assert response.status_code == 200
    assert response.json()["data"]["total_volume_kg"] is None


async def test_update_sequence_order(client, trainer_client_session):
    _, _, session = trainer_client_session
    create_resp = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json=_exercise_card(),
    )
    entry_id = create_resp.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/entries/{entry_id}",
        json={"sequence_order": 10},
    )
    assert response.status_code == 200
    assert response.json()["data"]["sequence_order"] == 10


async def test_update_performed_at(client, trainer_client_session):
    _, _, session = trainer_client_session
    create_resp = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json=_exercise_card(),
    )
    entry_id = create_resp.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/entries/{entry_id}",
        json={"performed_at": "2026-02-22T11:30:00Z"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["performed_at"] is not None


async def test_update_form_notes_array(client, trainer_client_session):
    _, _, session = trainer_client_session
    create_resp = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json=_exercise_card(),
    )
    entry_id = create_resp.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/entries/{entry_id}",
        json={"form_notes": ["Good lockout", "Watch knee cave"]},
    )
    assert response.status_code == 200
    assert response.json()["data"]["form_notes"] == ["Good lockout", "Watch knee cave"]


async def test_update_cue_effectiveness_jsonb(client, trainer_client_session):
    _, _, session = trainer_client_session
    create_resp = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json=_exercise_card(),
    )
    entry_id = create_resp.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/entries/{entry_id}",
        json={"cue_effectiveness": {"Chest up": "effective"}},
    )
    assert response.status_code == 200
    assert response.json()["data"]["cue_effectiveness"]["Chest up"] == "effective"


async def test_update_partial_preserves_unchanged(client, trainer_client_session):
    _, _, session = trainer_client_session
    create_resp = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json=_exercise_card(
            exercise_name="Squat",
            sets=[{"set_number": 1, "weight_kg": 100, "reps": 5}],
            form_notes=["Good depth"],
        ),
    )
    entry_id = create_resp.json()["data"]["id"]

    # Update only exercise_name
    response = await client.patch(
        f"/api/v1/entries/{entry_id}",
        json={"exercise_name": "Front Squat"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["exercise_name"] == "Front Squat"
    assert data["sets"] == [{"set_number": 1, "weight_kg": 100, "reps": 5}]
    assert data["form_notes"] == ["Good depth"]


async def test_update_sequence_order_zero_422(client, trainer_client_session):
    """PATCH with sequence_order=0 should fail validation, not 500."""
    _, _, session = trainer_client_session
    create_resp = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json=_exercise_card(),
    )
    entry_id = create_resp.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/entries/{entry_id}",
        json={"sequence_order": 0},
    )
    assert response.status_code == 422


async def test_update_empty_exercise_name_422(client, trainer_client_session):
    """PATCH with empty exercise_name should fail validation, not 500."""
    _, _, session = trainer_client_session
    create_resp = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json=_exercise_card(),
    )
    entry_id = create_resp.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/entries/{entry_id}",
        json={"exercise_name": ""},
    )
    assert response.status_code == 422


async def test_update_negative_volume_422(client, trainer_client_session):
    """PATCH with negative total_volume_kg should fail validation, not 500."""
    _, _, session = trainer_client_session
    create_resp = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json=_exercise_card(),
    )
    entry_id = create_resp.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/entries/{entry_id}",
        json={"total_volume_kg": -5.0},
    )
    assert response.status_code == 422


async def test_update_not_found_404(client, trainer_client_session):
    response = await client.patch(
        f"/api/v1/entries/{uuid.uuid4()}",
        json={"exercise_name": "Nope"},
    )
    assert response.status_code == 404


# --- Delete ---


async def test_delete_success_204(client, trainer_client_session):
    _, _, session = trainer_client_session
    create_resp = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json=_exercise_card(exercise_name="To Delete"),
    )
    entry_id = create_resp.json()["data"]["id"]

    response = await client.delete(f"/api/v1/entries/{entry_id}")
    assert response.status_code == 204


async def test_delete_not_found_404(client, trainer_client_session):
    response = await client.delete(f"/api/v1/entries/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_delete_verify_gone(client, trainer_client_session):
    _, _, session = trainer_client_session
    create_resp = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json=_exercise_card(exercise_name="Going Away"),
    )
    entry_id = create_resp.json()["data"]["id"]

    await client.delete(f"/api/v1/entries/{entry_id}")
    get_resp = await client.get(f"/api/v1/entries/{entry_id}")
    assert get_resp.status_code == 404


async def test_delete_doesnt_affect_other_entries(client, trainer_client_session, db_session):
    trainer, db_client, _ = trainer_client_session
    fresh_session = Session(
        trainer_id=trainer.id, client_id=db_client.id,
        started_at=datetime(2026, 2, 23, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(fresh_session)
    await db_session.flush()

    resp1 = await client.post(
        f"/api/v1/sessions/{fresh_session.id}/entries",
        json=_exercise_card(exercise_name="Keep Me"),
    )
    resp2 = await client.post(
        f"/api/v1/sessions/{fresh_session.id}/entries",
        json=_exercise_card(exercise_name="Delete Me"),
    )
    keep_id = resp1.json()["data"]["id"]
    delete_id = resp2.json()["data"]["id"]

    await client.delete(f"/api/v1/entries/{delete_id}")

    # The kept one should still be there
    get_resp = await client.get(f"/api/v1/entries/{keep_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["exercise_name"] == "Keep Me"


# --- Cascade + Ownership ---


async def test_session_delete_cascades_entries(client, trainer_client_session, db_session):
    trainer, db_client, _ = trainer_client_session
    cascade_session = Session(
        trainer_id=trainer.id, client_id=db_client.id,
        started_at=datetime(2026, 2, 23, 11, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(cascade_session)
    await db_session.flush()

    resp = await client.post(
        f"/api/v1/sessions/{cascade_session.id}/entries",
        json=_exercise_card(exercise_name="Will Cascade"),
    )
    entry_id = resp.json()["data"]["id"]

    # Delete the session
    await client.delete(f"/api/v1/sessions/{cascade_session.id}")

    # Entry should be gone
    get_resp = await client.get(f"/api/v1/entries/{entry_id}")
    assert get_resp.status_code == 404


async def test_entries_retain_correct_client_id(client, trainer_client_session):
    _, db_client, session = trainer_client_session
    resp = await client.post(
        f"/api/v1/sessions/{session.id}/entries",
        json=_exercise_card(),
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["client_id"] == str(db_client.id)


async def test_create_on_wrong_trainer_session_404(
    client, trainer_client_session, db_session,
):
    """Creating an entry on another trainer's session should return 404."""
    other_trainer = Trainer(
        email=f"other-{uuid.uuid4().hex[:8]}@test.com", name="Other Trainer",
    )
    db_session.add(other_trainer)
    await db_session.flush()

    other_client = Client(trainer_id=other_trainer.id, name="Other Client")
    db_session.add(other_client)
    await db_session.flush()

    other_session = Session(
        trainer_id=other_trainer.id, client_id=other_client.id,
        started_at=datetime(2026, 2, 22, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(other_session)
    await db_session.flush()

    response = await client.post(
        f"/api/v1/sessions/{other_session.id}/entries",
        json=_exercise_card(),
    )
    assert response.status_code == 404


async def test_get_wrong_trainer_entry_404(
    client, trainer_client_session, db_session,
):
    """Getting an entry owned by another trainer should return 404."""
    from app.models import SessionEntry
    from app.models import EntryTypeEnum as ETE

    other_trainer = Trainer(
        email=f"other2-{uuid.uuid4().hex[:8]}@test.com", name="Other Trainer 2",
    )
    db_session.add(other_trainer)
    await db_session.flush()

    other_client = Client(trainer_id=other_trainer.id, name="Other Client 2")
    db_session.add(other_client)
    await db_session.flush()

    other_session = Session(
        trainer_id=other_trainer.id, client_id=other_client.id,
        started_at=datetime(2026, 2, 22, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(other_session)
    await db_session.flush()

    entry = SessionEntry(
        session_id=other_session.id,
        client_id=other_client.id,
        entry_type=ETE.exercise_card,
        sequence_order=1,
        exercise_name="Secret Squat",
    )
    db_session.add(entry)
    await db_session.flush()

    response = await client.get(f"/api/v1/entries/{entry.id}")
    assert response.status_code == 404


async def test_update_wrong_trainer_entry_404(
    client, trainer_client_session, db_session,
):
    """Updating an entry owned by another trainer should return 404."""
    from app.models import SessionEntry
    from app.models import EntryTypeEnum as ETE

    other_trainer = Trainer(
        email=f"other-upd-{uuid.uuid4().hex[:8]}@test.com", name="Other Trainer Upd",
    )
    db_session.add(other_trainer)
    await db_session.flush()

    other_client = Client(trainer_id=other_trainer.id, name="Other Client Upd")
    db_session.add(other_client)
    await db_session.flush()

    other_session = Session(
        trainer_id=other_trainer.id, client_id=other_client.id,
        started_at=datetime(2026, 2, 22, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(other_session)
    await db_session.flush()

    entry = SessionEntry(
        session_id=other_session.id, client_id=other_client.id,
        entry_type=ETE.exercise_card, sequence_order=1, exercise_name="Secret",
    )
    db_session.add(entry)
    await db_session.flush()

    response = await client.patch(
        f"/api/v1/entries/{entry.id}", json={"exercise_name": "Hacked"},
    )
    assert response.status_code == 404


async def test_delete_wrong_trainer_entry_404(
    client, trainer_client_session, db_session,
):
    """Deleting an entry owned by another trainer should return 404."""
    from app.models import SessionEntry
    from app.models import EntryTypeEnum as ETE

    other_trainer = Trainer(
        email=f"other-del-{uuid.uuid4().hex[:8]}@test.com", name="Other Trainer Del",
    )
    db_session.add(other_trainer)
    await db_session.flush()

    other_client = Client(trainer_id=other_trainer.id, name="Other Client Del")
    db_session.add(other_client)
    await db_session.flush()

    other_session = Session(
        trainer_id=other_trainer.id, client_id=other_client.id,
        started_at=datetime(2026, 2, 22, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(other_session)
    await db_session.flush()

    entry = SessionEntry(
        session_id=other_session.id, client_id=other_client.id,
        entry_type=ETE.exercise_card, sequence_order=1, exercise_name="Secret",
    )
    db_session.add(entry)
    await db_session.flush()

    response = await client.delete(f"/api/v1/entries/{entry.id}")
    assert response.status_code == 404


async def test_list_entries_on_wrong_trainer_session_404(
    client, trainer_client_session, db_session,
):
    """Listing entries for another trainer's session should return 404."""
    other_trainer = Trainer(
        email=f"other3-{uuid.uuid4().hex[:8]}@test.com", name="Other Trainer 3",
    )
    db_session.add(other_trainer)
    await db_session.flush()

    other_client = Client(trainer_id=other_trainer.id, name="Other Client 3")
    db_session.add(other_client)
    await db_session.flush()

    other_session = Session(
        trainer_id=other_trainer.id, client_id=other_client.id,
        started_at=datetime(2026, 2, 22, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(other_session)
    await db_session.flush()

    response = await client.get(f"/api/v1/sessions/{other_session.id}/entries")
    assert response.status_code == 404


async def test_list_entries_by_wrong_trainer_client_404(
    client, trainer_client_session, db_session,
):
    """Listing entries for another trainer's client should return 404."""
    other_trainer = Trainer(
        email=f"other-elc-{uuid.uuid4().hex[:8]}@test.com", name="Other ELC Trainer",
    )
    db_session.add(other_trainer)
    await db_session.flush()

    other_client = Client(trainer_id=other_trainer.id, name="Other ELC Client")
    db_session.add(other_client)
    await db_session.flush()

    response = await client.get(f"/api/v1/clients/{other_client.id}/entries")
    assert response.status_code == 404
