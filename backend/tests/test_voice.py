"""Tests for the voice clip endpoint — full pipeline integration tests
with mocked Deepgram and Claude, real DB persistence."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Client, EntryTypeEnum, Session, SessionEntry, Trainer


# ===================================================================
# Mock helpers
# ===================================================================


def _make_deepgram_mock(
    transcript: str = "three sets of bench press at 80 kilos",
    confidence: float = 0.95,
    duration: float = 3.5,
) -> MagicMock:
    """Build a mock Deepgram response that transcribe_audio returns."""
    mock_alternative = MagicMock()
    mock_alternative.transcript = transcript
    mock_alternative.confidence = confidence
    mock_alternative.words = []

    mock_channel = MagicMock()
    mock_channel.alternatives = [mock_alternative]

    mock_results = MagicMock()
    mock_results.channels = [mock_channel]

    mock_metadata = MagicMock()
    mock_metadata.duration = duration

    mock_response = MagicMock()
    mock_response.results = mock_results
    mock_response.metadata = mock_metadata

    return mock_response


def _make_tool_use_block(name: str, tool_input: dict) -> MagicMock:
    """Build a mock Claude tool_use content block."""
    block = MagicMock()
    block.type = "tool_use"
    block.id = "toolu_test"
    block.name = name
    block.input = tool_input
    return block


def _make_claude_response(tool_calls: list[MagicMock]) -> MagicMock:
    """Build a mock Claude messages.create() response."""
    response = MagicMock()
    response.content = tool_calls
    return response


def _patch_both(
    transcript: str = "three sets of bench press at 80 kilos",
    confidence: float = 0.95,
    duration: float = 3.5,
    tool_calls: list[MagicMock] | None = None,
):
    """Return (deepgram_patch, claude_patch) context managers.

    Usage:
        dg = _make_deepgram_mock(...)
        tool_calls = [_make_tool_use_block(...)]
        with _patch_both(..., tool_calls=tool_calls):
            response = await client.post(...)
    """
    dg_response = _make_deepgram_mock(transcript, confidence, duration)
    dg_mock = AsyncMock()
    dg_mock.listen.asyncrest = AsyncMock()
    dg_mock.listen.asyncrest.transcribe_file = AsyncMock(return_value=dg_response)

    claude_response = _make_claude_response(tool_calls or [])
    claude_mock = AsyncMock()
    claude_mock.messages.create = AsyncMock(return_value=claude_response)

    dg_patch = patch(
        "app.services.transcription.DeepgramClient",
        return_value=dg_mock,
    )
    claude_patch = patch(
        "app.services.parser.anthropic.AsyncAnthropic",
        return_value=claude_mock,
    )

    class CombinedPatch:
        def __enter__(self):
            self._dg = dg_patch.__enter__()
            self._claude = claude_patch.__enter__()
            return self

        def __exit__(self, *args):
            claude_patch.__exit__(*args)
            dg_patch.__exit__(*args)

    return CombinedPatch()


# ===================================================================
# Fixtures
# ===================================================================


@pytest_asyncio.fixture(loop_scope="session")
async def voice_fixtures(
    db_session: AsyncSession, trainer_for_api: Trainer,
) -> tuple[Trainer, Client, Session]:
    """Create trainer + client + session for voice tests."""
    client = Client(
        trainer_id=trainer_for_api.id,
        name="Voice Test Client",
        preferred_weight_unit="kg",
    )
    db_session.add(client)
    await db_session.flush()

    session = Session(
        trainer_id=trainer_for_api.id,
        client_id=client.id,
        started_at=datetime(2026, 2, 24, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(session)
    await db_session.flush()

    return trainer_for_api, client, session


# ===================================================================
# Tests
# ===================================================================


@pytest.mark.asyncio(loop_scope="session")
class TestVoiceClipEndpoint:

    async def test_single_exercise_card(self, client, voice_fixtures):
        """Happy path: audio → single exercise entry created in DB."""
        _, _, session = voice_fixtures
        tool_calls = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "bench press",
                "sets": [
                    {"reps": 10, "weight": 80, "weight_unit": "kg"},
                    {"reps": 10, "weight": 80, "weight_unit": "kg"},
                    {"reps": 10, "weight": 80, "weight_unit": "kg"},
                ],
            })
        ]

        with _patch_both(tool_calls=tool_calls):
            response = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )

        assert response.status_code == 201
        data = response.json()["data"]
        assert len(data["entries_created"]) == 1
        entry = data["entries_created"][0]
        assert entry["entry_type"] == "exercise_card"
        assert entry["exercise_name"] == "bench press"
        assert len(entry["sets"]) == 3
        assert entry["sets"][0]["reps"] == 10
        assert entry["sets"][0]["weight"] == 80
        assert data["transcript"] == "three sets of bench press at 80 kilos"
        assert data["confidence"] == 0.95

    async def test_observation_card(self, client, voice_fixtures):
        """Yellow observation → clarification, not a persisted entry."""
        _, _, session = voice_fixtures
        tool_calls = [
            _make_tool_use_block("record_observation_card", {
                "observation_text": "Client seems tired today, low energy",
                "flag_color": "yellow",
                "flag_reason": "fatigue observed",
            })
        ]

        with _patch_both(
            transcript="client seems tired today",
            tool_calls=tool_calls,
        ):
            response = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )

        assert response.status_code == 201
        data = response.json()["data"]
        # Yellow observations are clarifications, not persisted entries
        assert len(data["entries_created"]) == 0
        assert len(data["clarifications_needed"]) == 1
        assert data["clarifications_needed"][0]["observation_text"] == "Client seems tired today, low energy"

    async def test_multiple_cards(self, client, voice_fixtures):
        """Two tool calls → two entries created."""
        _, _, session = voice_fixtures
        tool_calls = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "squat",
                "sets": [{"reps": 5, "weight": 100, "weight_unit": "kg"}],
            }),
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "leg press",
                "sets": [{"reps": 12, "weight": 150, "weight_unit": "kg"}],
            }),
        ]

        with _patch_both(
            transcript="squat five at 100, then leg press twelve at 150",
            tool_calls=tool_calls,
        ):
            response = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )

        assert response.status_code == 201
        data = response.json()["data"]
        assert len(data["entries_created"]) == 2
        names = [e["exercise_name"] for e in data["entries_created"]]
        assert "squat" in names
        assert "leg press" in names

    async def test_modification_updates_existing(
        self, client, db_session, voice_fixtures,
    ):
        """modify_exercise_card applied to an existing DB entry."""
        _, db_client, session = voice_fixtures

        # Count existing entries so we target the right one
        result = await db_session.execute(
            select(SessionEntry)
            .where(SessionEntry.session_id == session.id)
            .order_by(SessionEntry.sequence_order.asc())
        )
        existing_count = len(list(result.scalars().all()))

        # Get next sequence_order to avoid duplicates
        from app.services import entry_service
        next_seq = await entry_service.get_next_sequence_order(db_session, session.id)

        # Create an existing entry to modify
        existing = SessionEntry(
            session_id=session.id,
            client_id=db_client.id,
            entry_type=EntryTypeEnum.exercise_card,
            sequence_order=next_seq,
            exercise_name="squat",
            sets=[
                {"reps": 5, "weight": 100, "weight_unit": "kg"},
                {"reps": 5, "weight": 100, "weight_unit": "kg"},
            ],
        )
        db_session.add(existing)
        await db_session.flush()

        # Target the entry we just created (1-indexed position in context)
        target_id = existing_count + 1

        tool_calls = [
            _make_tool_use_block("modify_exercise_card", {
                "target_entry_id": target_id,
                "action": "add",
                "updates": {"rpe": 8},
            })
        ]

        with _patch_both(
            transcript="RPE 8 on those squats",
            tool_calls=tool_calls,
        ):
            response = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )

        assert response.status_code == 201
        data = response.json()["data"]
        assert len(data["entries_modified"]) == 1
        modified = data["entries_modified"][0]
        # RPE should be added to all sets
        for s in modified["sets"]:
            assert s["rpe"] == 8

    async def test_modification_preserves_unrelated_fields(
        self, client, db_session, voice_fixtures,
    ):
        """Modifying RPE should not wipe form_notes or cues_given."""
        _, db_client, session = voice_fixtures

        result = await db_session.execute(
            select(SessionEntry)
            .where(SessionEntry.session_id == session.id)
            .order_by(SessionEntry.sequence_order.asc())
        )
        existing_count = len(list(result.scalars().all()))

        from app.services import entry_service
        next_seq = await entry_service.get_next_sequence_order(db_session, session.id)

        # Create entry with form_notes and cues_given populated
        existing = SessionEntry(
            session_id=session.id,
            client_id=db_client.id,
            entry_type=EntryTypeEnum.exercise_card,
            sequence_order=next_seq,
            exercise_name="squat",
            sets=[{"reps": 5, "weight": 100, "weight_unit": "kg"}],
            form_notes=["good depth", "knees tracking well"],
            cues_given=["drive through heels"],
        )
        db_session.add(existing)
        await db_session.flush()

        target_id = existing_count + 1

        tool_calls = [
            _make_tool_use_block("modify_exercise_card", {
                "target_entry_id": target_id,
                "action": "add",
                "updates": {"rpe": 9},
            })
        ]

        with _patch_both(
            transcript="RPE 9 on those squats",
            tool_calls=tool_calls,
        ):
            response = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )

        assert response.status_code == 201
        data = response.json()["data"]
        assert len(data["entries_modified"]) == 1
        modified = data["entries_modified"][0]

        # RPE applied
        assert modified["sets"][0]["rpe"] == 9
        # form_notes and cues_given preserved
        assert modified["form_notes"] == ["good depth", "knees tracking well"]
        assert modified["cues_given"] == ["drive through heels"]

    async def test_clarification_not_persisted(
        self, client, db_session, voice_fixtures,
    ):
        """Yellow observation → in clarifications_needed, NOT persisted to DB."""
        _, _, session = voice_fixtures

        # Count entries before
        result = await db_session.execute(
            select(SessionEntry).where(SessionEntry.session_id == session.id)
        )
        entries_before = len(list(result.scalars().all()))

        tool_calls = [
            _make_tool_use_block("record_observation_card", {
                "observation_text": "Did you mean bench press or incline bench?",
                "flag_color": "yellow",
                "flag_reason": "ambiguous exercise reference",
            })
        ]

        with _patch_both(
            transcript="bench something",
            tool_calls=tool_calls,
        ):
            response = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )

        assert response.status_code == 201
        data = response.json()["data"]
        assert len(data["clarifications_needed"]) == 1
        assert len(data["entries_created"]) == 0

        # Verify nothing was persisted
        result = await db_session.execute(
            select(SessionEntry).where(SessionEntry.session_id == session.id)
        )
        entries_after = len(list(result.scalars().all()))
        assert entries_after == entries_before

    async def test_non_yellow_observation_persisted(self, client, voice_fixtures):
        """Non-yellow observation cards ARE persisted as entries."""
        _, _, session = voice_fixtures
        tool_calls = [
            _make_tool_use_block("record_observation_card", {
                "observation_text": "Client reported sharp knee pain during squats",
                "flag_color": "red",
                "flag_reason": "pain reported",
            })
        ]

        with _patch_both(
            transcript="knee hurts during squats",
            tool_calls=tool_calls,
        ):
            response = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )

        assert response.status_code == 201
        data = response.json()["data"]
        assert len(data["entries_created"]) == 1
        entry = data["entries_created"][0]
        assert entry["entry_type"] == "observation_card"
        assert entry["flag_color"] == "red"

    async def test_observation_with_set_attachment_persisted(self, client, voice_fixtures):
        """Observation with attached_to_set flows through pipeline to DB."""
        _, _, session = voice_fixtures

        # First create an exercise entry so context_entry_count > 0
        exercise_tool = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "clamshells",
                "sets": [{"reps": 15}, {"reps": 15}],
            }),
        ]
        with _patch_both(transcript="clamshells 2 sets of 15", tool_calls=exercise_tool):
            resp1 = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )
        assert resp1.status_code == 201

        # Now send observation targeting that exercise, set 1
        obs_tool = [
            _make_tool_use_block("record_observation_card", {
                "observation_text": "Left weaker than right on clamshells",
                "target_entry_id": 1,
                "attached_to_set": 1,
            }),
        ]
        with _patch_both(
            transcript="left is tougher than right",
            tool_calls=obs_tool,
        ):
            resp2 = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )

        assert resp2.status_code == 201
        data = resp2.json()["data"]
        assert len(data["entries_created"]) == 1
        entry = data["entries_created"][0]
        assert entry["entry_type"] == "observation_card"
        assert entry["attached_to_set"] == 1

    async def test_observation_without_attachment_no_set_stored(self, client, voice_fixtures):
        """Session-level observation — attached_to_set stays None."""
        _, _, session = voice_fixtures
        tool_calls = [
            _make_tool_use_block("record_observation_card", {
                "observation_text": "Energy dropping mid-session",
                "flag_color": "yellow",
                "flag_reason": "fatigue",
            }),
        ]
        # Yellow observations become clarifications, not persisted entries.
        # Use a non-yellow observation for this test.
        tool_calls_green = [
            _make_tool_use_block("record_observation_card", {
                "observation_text": "Good energy today",
                "flag_color": "green",
                "flag_reason": "positive session",
            }),
        ]
        with _patch_both(
            transcript="good energy today",
            tool_calls=tool_calls_green,
        ):
            response = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )

        assert response.status_code == 201
        data = response.json()["data"]
        assert len(data["entries_created"]) == 1
        entry = data["entries_created"][0]
        assert entry["attached_to_set"] is None

    async def test_observation_invalid_target_cleared_in_pipeline(
        self, client, voice_fixtures,
    ):
        """Observation targets entry [5] but session has no entries → cleared."""
        _, _, session = voice_fixtures
        obs_tool = [
            _make_tool_use_block("record_observation_card", {
                "observation_text": "Form issue on squats",
                "target_entry_id": 5,
                "attached_to_set": 2,
            }),
        ]
        with _patch_both(
            transcript="form issue on squats",
            tool_calls=obs_tool,
        ):
            response = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )

        assert response.status_code == 201
        data = response.json()["data"]
        # Should still be persisted (not yellow-flagged)
        assert len(data["entries_created"]) == 1
        entry = data["entries_created"][0]
        # But attachment should have been cleared by validation
        assert entry["attached_to_set"] is None
        # Should have a warning about invalid target
        assert any(w["code"] in ("invalid_target", "no_context")
                    for w in data["warnings"])

    async def test_session_not_found(self, client, voice_fixtures):
        """Random session_id → 404."""
        fake_id = uuid.uuid4()
        with _patch_both():
            response = await client.post(
                f"/api/v1/sessions/{fake_id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )
        assert response.status_code == 404

    async def test_wrong_trainer(self, client, db_session, voice_fixtures):
        """Other trainer's session → 404."""
        other_trainer = Trainer(
            email=f"other-{uuid.uuid4().hex[:8]}@test.com",
            name="Other Trainer",
        )
        db_session.add(other_trainer)
        await db_session.flush()

        other_client = Client(trainer_id=other_trainer.id, name="Other Client")
        db_session.add(other_client)
        await db_session.flush()

        other_session = Session(
            trainer_id=other_trainer.id,
            client_id=other_client.id,
            started_at=datetime(2026, 2, 24, 10, 0, 0, tzinfo=timezone.utc),
        )
        db_session.add(other_session)
        await db_session.flush()

        with _patch_both():
            response = await client.post(
                f"/api/v1/sessions/{other_session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )
        assert response.status_code == 404

    async def test_empty_audio(self, client, voice_fixtures):
        """Empty bytes → 422."""
        _, _, session = voice_fixtures
        response = await client.post(
            f"/api/v1/sessions/{session.id}/voice-clip",
            files={"audio": ("test.wav", b"", "audio/wav")},
        )
        assert response.status_code == 422

    async def test_unsupported_mime_type(self, client, voice_fixtures):
        """Non-audio MIME type → 422."""
        _, _, session = voice_fixtures
        response = await client.post(
            f"/api/v1/sessions/{session.id}/voice-clip",
            files={"audio": ("test.txt", b"not audio", "text/plain")},
        )
        assert response.status_code == 422
        assert "Unsupported audio type" in response.json()["error"]["message"]

    async def test_oversized_audio(self, client, voice_fixtures):
        """Audio exceeding 25 MB → 422."""
        _, _, session = voice_fixtures
        # Create data just over the limit (25 MB + 1 byte)
        from app.api.voice import MAX_AUDIO_SIZE_BYTES
        oversized = b"x" * (MAX_AUDIO_SIZE_BYTES + 1)
        response = await client.post(
            f"/api/v1/sessions/{session.id}/voice-clip",
            files={"audio": ("test.wav", oversized, "audio/wav")},
        )
        assert response.status_code == 422
        assert "too large" in response.json()["error"]["message"]

    async def test_empty_transcript(self, client, voice_fixtures):
        """Silence → 201, empty entries, transcript=""."""
        _, _, session = voice_fixtures

        with _patch_both(transcript="", confidence=0.0):
            response = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-silence", "audio/wav")},
            )

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["transcript"] == ""
        assert len(data["entries_created"]) == 0
        assert len(data["entries_modified"]) == 0

    async def test_timing_populated(self, client, voice_fixtures):
        """All timing fields are integers >= 0."""
        _, _, session = voice_fixtures
        tool_calls = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "deadlift",
                "sets": [{"reps": 5}],
            })
        ]

        with _patch_both(transcript="deadlift five reps", tool_calls=tool_calls):
            response = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )

        assert response.status_code == 201
        timing = response.json()["data"]["timing"]
        assert isinstance(timing["transcription_ms"], int)
        assert isinstance(timing["parsing_ms"], int)
        assert isinstance(timing["validation_ms"], int)
        assert isinstance(timing["persistence_ms"], int)
        assert isinstance(timing["total_ms"], int)
        assert timing["transcription_ms"] >= 0
        assert timing["parsing_ms"] >= 0
        assert timing["validation_ms"] >= 0
        assert timing["persistence_ms"] >= 0
        assert timing["total_ms"] >= 0
        assert timing["total_ms"] == (
            timing["transcription_ms"] + timing["parsing_ms"]
            + timing["validation_ms"] + timing["persistence_ms"]
        )

    async def test_warnings_propagated(self, client, voice_fixtures):
        """Suspicious reps → warning in response."""
        _, _, session = voice_fixtures
        tool_calls = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "curl",
                "sets": [{"reps": 999, "weight": 10, "weight_unit": "kg"}],
            })
        ]

        with _patch_both(transcript="curl 999 reps at 10", tool_calls=tool_calls):
            response = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )

        assert response.status_code == 201
        data = response.json()["data"]
        assert len(data["warnings"]) > 0
        codes = [w["code"] for w in data["warnings"]]
        assert "suspicious_reps" in codes

    async def test_exercise_fuzzy_match(self, client, voice_fixtures):
        """Exercise name fuzzy-matched to canonical DB name."""
        _, _, session = voice_fixtures
        tool_calls = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "bench",
                "sets": [{"reps": 10, "weight": 80, "weight_unit": "kg"}],
            })
        ]

        with _patch_both(transcript="bench ten at 80", tool_calls=tool_calls):
            response = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )

        assert response.status_code == 201
        data = response.json()["data"]
        assert len(data["entries_created"]) == 1
        entry = data["entries_created"][0]
        # "bench" should fuzzy-match to "Barbell Bench Press" from the exercise DB
        assert entry["exercise_canonical"] is not None
        assert "bench press" in entry["exercise_canonical"].lower()


# ===================================================================
# Step 1: Helper Function Unit Tests
# ===================================================================


class TestVoiceHelpers:
    """Direct tests for services/voice.py helper functions.

    No HTTP, no mocks, no DB — pure function tests.
    """

    def test_entry_to_context_dict_exercise(self):
        """Exercise card → dict with exercise_name, sets, form_notes, cues_given."""
        from app.services.voice import _entry_to_context_dict

        entry = MagicMock()
        entry.entry_type = EntryTypeEnum.exercise_card
        entry.exercise_name = "squat"
        entry.sets = [{"reps": 5, "weight": 100, "weight_unit": "kg"}]
        entry.form_notes = ["Keep chest up"]
        entry.cues_given = ["Drive through heels"]

        result = _entry_to_context_dict(entry)

        assert result["entry_type"] == "exercise_card"
        assert result["exercise_name"] == "squat"
        assert result["sets"] == [{"reps": 5, "weight": 100, "weight_unit": "kg"}]
        assert result["form_notes"] == ["Keep chest up"]
        assert result["cues_given"] == ["Drive through heels"]

    def test_entry_to_context_dict_observation(self):
        """Observation card → dict with observation_text, flag_color, flag_reason."""
        from app.services.voice import _entry_to_context_dict

        entry = MagicMock()
        entry.entry_type = EntryTypeEnum.observation_card
        entry.observation_text = "Client looks fatigued"
        entry.flag_color = "red"
        entry.flag_reason = "fatigue"

        result = _entry_to_context_dict(entry)

        assert result["entry_type"] == "observation_card"
        assert result["observation_text"] == "Client looks fatigued"
        assert result["flag_color"] == "red"
        assert result["flag_reason"] == "fatigue"
        assert "exercise_name" not in result

    def test_entry_to_context_dict_minimal(self):
        """Exercise with no sets/notes/cues → only entry_type + exercise_name."""
        from app.services.voice import _entry_to_context_dict

        entry = MagicMock()
        entry.entry_type = EntryTypeEnum.exercise_card
        entry.exercise_name = "pullups"
        entry.sets = None
        entry.form_notes = None
        entry.cues_given = None

        result = _entry_to_context_dict(entry)

        assert result == {
            "entry_type": "exercise_card",
            "exercise_name": "pullups",
        }

    def test_validated_set_to_db_format_full(self):
        """ValidatedSet with all fields → correct DB dict."""
        from app.services.validation import ValidatedSet
        from app.services.voice import _validated_set_to_db_format

        vs = ValidatedSet(
            reps=10,
            weight_kg=80.0,
            weight_original=80.0,
            weight_unit_original="kg",
            rpe=7.5,
            duration_seconds=45,
        )
        result = _validated_set_to_db_format(vs)

        assert result == {
            "reps": 10,
            "weight": 80.0,
            "weight_unit": "kg",
            "weight_original": 80.0,
            "weight_unit_original": "kg",
            "rpe": 7.5,
            "duration_seconds": 45,
        }

    def test_validated_set_to_db_format_bodyweight(self):
        """ValidatedSet(reps=10) with no weight → {"reps": 10} only."""
        from app.services.validation import ValidatedSet
        from app.services.voice import _validated_set_to_db_format

        vs = ValidatedSet(reps=10)
        result = _validated_set_to_db_format(vs)

        assert result == {"reps": 10}

    def test_validated_set_to_db_format_with_rir(self):
        """ValidatedSet with rir → includes rir in DB dict."""
        from app.services.validation import ValidatedSet
        from app.services.voice import _validated_set_to_db_format

        vs = ValidatedSet(reps=5, weight_kg=100.0, weight_original=100.0, weight_unit_original="kg", rir=2.0, rpe=8.0)
        result = _validated_set_to_db_format(vs)

        assert result["rir"] == 2.0
        assert result["rpe"] == 8.0

    def test_validated_set_to_db_format_with_equipment_note(self):
        """ValidatedSet with equipment_note → includes it in DB dict."""
        from app.services.validation import ValidatedSet
        from app.services.voice import _validated_set_to_db_format

        vs = ValidatedSet(reps=6, weight_kg=60.0, weight_original=60.0, weight_unit_original="kg", equipment_note="with a red band")
        result = _validated_set_to_db_format(vs)

        assert result["equipment_note"] == "with a red band"

    def test_validated_set_to_db_format_rir_none_excluded(self):
        """ValidatedSet with rir=None → rir key should NOT be in dict."""
        from app.services.validation import ValidatedSet
        from app.services.voice import _validated_set_to_db_format

        vs = ValidatedSet(reps=10)
        result = _validated_set_to_db_format(vs)

        assert "rir" not in result
        assert "equipment_note" not in result

    def test_validated_sets_to_db_format_none(self):
        """None input → None output."""
        from app.services.voice import _validated_sets_to_db_format

        assert _validated_sets_to_db_format(None) is None

    def test_build_modification_kwargs_rpe(self):
        """RPE update applied to all sets."""
        from app.services.validation import ValidatedModification
        from app.services.voice import _build_modification_kwargs

        entry = MagicMock()
        entry.sets = [
            {"reps": 5, "weight": 100, "weight_unit": "kg"},
            {"reps": 5, "weight": 100, "weight_unit": "kg"},
        ]
        entry.form_notes = None
        entry.cues_given = None

        mod = ValidatedModification(
            target_entry_id=1,
            action="add",
            target_sets=None,
            updates={"rpe": 8},
            form_notes=(),
            cues_given=(),
            warnings=(),
        )

        kwargs = _build_modification_kwargs(entry, mod)

        assert "sets" in kwargs
        for s in kwargs["sets"]:
            assert s["rpe"] == 8
            assert s["weight"] == 100  # original weight unchanged

    def test_build_modification_kwargs_weight_normalized(self):
        """Weight keys mapped correctly — raw weight/weight_unit skipped.

        Uses lbs values so raw and normalized differ. If the guard
        (continue on 'weight'/'weight_unit') were broken, weight_unit
        would end up as 'lbs' instead of 'kg', and weight would be 185
        instead of 83.9.
        """
        from app.services.validation import ValidatedModification
        from app.services.voice import _build_modification_kwargs

        entry = MagicMock()
        entry.sets = [{"reps": 5, "weight": 100, "weight_unit": "kg"}]
        entry.form_notes = None
        entry.cues_given = None

        # validate_modification produces this when weight is present:
        # normalized keys (weight_kg, weight_original, weight_unit_original)
        # plus the raw keys (weight, weight_unit) still in the dict.
        # The guard must skip raw keys so only normalized ones apply.
        mod = ValidatedModification(
            target_entry_id=1,
            action="correct",
            target_sets=None,
            updates={
                "weight": 185,
                "weight_unit": "lbs",
                "weight_kg": 83.9,
                "weight_original": 185,
                "weight_unit_original": "lbs",
            },
            form_notes=(),
            cues_given=(),
            warnings=(),
        )

        kwargs = _build_modification_kwargs(entry, mod)

        s = kwargs["sets"][0]
        # weight_kg path sets weight to 83.9 and weight_unit to "kg"
        # If the guard were broken, weight would be 185 and weight_unit "lbs"
        assert s["weight"] == 83.9
        assert s["weight_unit"] == "kg"
        assert s["weight_original"] == 185
        assert s["weight_unit_original"] == "lbs"

    def test_build_modification_kwargs_form_notes_only(self):
        """Form notes with no updates → {"form_notes": [...]}."""
        from app.services.validation import ValidatedModification
        from app.services.voice import _build_modification_kwargs

        entry = MagicMock()
        entry.sets = [{"reps": 5}]
        entry.form_notes = ["Existing note"]
        entry.cues_given = None

        mod = ValidatedModification(
            target_entry_id=1,
            action="add",
            target_sets=None,
            updates=None,
            form_notes=("Good depth",),
            cues_given=(),
            warnings=(),
        )

        kwargs = _build_modification_kwargs(entry, mod)

        assert "sets" not in kwargs
        assert kwargs["form_notes"] == ["Existing note", "Good depth"]

    def test_build_modification_kwargs_cues_only(self):
        """Cues with no updates → {"cues_given": [...]}."""
        from app.services.validation import ValidatedModification
        from app.services.voice import _build_modification_kwargs

        entry = MagicMock()
        entry.sets = None
        entry.form_notes = None
        entry.cues_given = ["Brace core"]

        mod = ValidatedModification(
            target_entry_id=1,
            action="add",
            target_sets=None,
            updates=None,
            form_notes=(),
            cues_given=("Squeeze at top",),
            warnings=(),
        )

        kwargs = _build_modification_kwargs(entry, mod)

        assert "sets" not in kwargs
        assert kwargs["cues_given"] == ["Brace core", "Squeeze at top"]

    def test_build_modification_kwargs_target_sets(self):
        """target_sets=[2] → only set index 1 updated."""
        from app.services.validation import ValidatedModification
        from app.services.voice import _build_modification_kwargs

        entry = MagicMock()
        entry.sets = [
            {"reps": 5, "weight": 100, "weight_unit": "kg"},
            {"reps": 5, "weight": 100, "weight_unit": "kg"},
            {"reps": 5, "weight": 100, "weight_unit": "kg"},
        ]
        entry.form_notes = None
        entry.cues_given = None

        mod = ValidatedModification(
            target_entry_id=1,
            action="add",
            target_sets=(2,),  # 1-indexed → targets set index 1
            updates={"rpe": 9},
            form_notes=(),
            cues_given=(),
            warnings=(),
        )

        kwargs = _build_modification_kwargs(entry, mod)

        assert "rpe" not in kwargs["sets"][0]  # set 0 untouched
        assert kwargs["sets"][1]["rpe"] == 9   # set 1 updated
        assert "rpe" not in kwargs["sets"][2]  # set 2 untouched

    def test_build_modification_kwargs_no_sets_on_entry(self):
        """Entry has no sets + updates dict → empty kwargs (no crash)."""
        from app.services.validation import ValidatedModification
        from app.services.voice import _build_modification_kwargs

        entry = MagicMock()
        entry.sets = None
        entry.form_notes = None
        entry.cues_given = None

        mod = ValidatedModification(
            target_entry_id=1,
            action="add",
            target_sets=None,
            updates={"rpe": 8},
            form_notes=(),
            cues_given=(),
            warnings=(),
        )

        kwargs = _build_modification_kwargs(entry, mod)

        assert kwargs == {}


# ===================================================================
# Step 2: Weight Unit Integration Tests
# ===================================================================


@pytest_asyncio.fixture(loop_scope="session")
async def lbs_voice_fixtures(
    db_session: AsyncSession, trainer_for_api: Trainer,
) -> tuple[Trainer, Client, Session]:
    """Trainer + client (preferred_weight_unit=lbs) + session."""
    lbs_client = Client(
        trainer_id=trainer_for_api.id,
        name="Lbs Client",
        preferred_weight_unit="lbs",
    )
    db_session.add(lbs_client)
    await db_session.flush()

    session = Session(
        trainer_id=trainer_for_api.id,
        client_id=lbs_client.id,
        started_at=datetime(2026, 2, 24, 11, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(session)
    await db_session.flush()

    return trainer_for_api, lbs_client, session


@pytest_asyncio.fixture(loop_scope="session")
async def no_unit_voice_fixtures(
    db_session: AsyncSession, trainer_for_api: Trainer,
) -> tuple[Trainer, Client, Session]:
    """Trainer + client (preferred_weight_unit=None) + session."""
    no_unit_client = Client(
        trainer_id=trainer_for_api.id,
        name="No Unit Client",
        preferred_weight_unit=None,
    )
    db_session.add(no_unit_client)
    await db_session.flush()

    session = Session(
        trainer_id=trainer_for_api.id,
        client_id=no_unit_client.id,
        started_at=datetime(2026, 2, 24, 12, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(session)
    await db_session.flush()

    return trainer_for_api, no_unit_client, session


@pytest.mark.asyncio(loop_scope="session")
class TestWeightUnitHandling:

    async def test_lbs_client_weight_stored_as_kg(
        self, client, lbs_voice_fixtures,
    ):
        """Client with preferred_weight_unit='lbs' → weight converted to kg."""
        _, _, session = lbs_voice_fixtures
        tool_calls = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "bench press",
                "sets": [{"reps": 10, "weight": 135, "weight_unit": "lbs"}],
            })
        ]

        with _patch_both(
            transcript="bench press 135 pounds",
            tool_calls=tool_calls,
        ):
            response = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )

        assert response.status_code == 201
        data = response.json()["data"]
        assert len(data["entries_created"]) == 1
        s = data["entries_created"][0]["sets"][0]
        # 135 lbs × 0.453592 = 61.2 kg (rounded to 1 decimal)
        assert s["weight"] == pytest.approx(61.2, abs=0.1)
        assert s["weight_unit"] == "kg"
        assert s["weight_original"] == 135
        assert s["weight_unit_original"] == "lbs"

    async def test_kg_client_weight_unchanged(self, client, voice_fixtures):
        """Client with preferred_weight_unit='kg' → weight stored as-is."""
        _, _, session = voice_fixtures
        tool_calls = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "squat",
                "sets": [{"reps": 5, "weight": 100, "weight_unit": "kg"}],
            })
        ]

        with _patch_both(
            transcript="squat 100 kilos",
            tool_calls=tool_calls,
        ):
            response = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )

        assert response.status_code == 201
        s = response.json()["data"]["entries_created"][0]["sets"][0]
        assert s["weight"] == 100.0
        assert s["weight_unit"] == "kg"

    async def test_no_preferred_unit_defaults_to_kg(
        self, client, no_unit_voice_fixtures,
    ):
        """Client with preferred_weight_unit=None → treated as kg."""
        _, _, session = no_unit_voice_fixtures
        tool_calls = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "deadlift",
                "sets": [{"reps": 5, "weight": 100}],
            })
        ]

        with _patch_both(
            transcript="deadlift 100",
            tool_calls=tool_calls,
        ):
            response = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )

        assert response.status_code == 201
        s = response.json()["data"]["entries_created"][0]["sets"][0]
        # No preferred unit → defaults to kg, weight stored unchanged
        assert s["weight"] == 100.0
        assert s["weight_unit"] == "kg"


# ===================================================================
# Step 3: Modification Edge Cases
# ===================================================================


@pytest.mark.asyncio(loop_scope="session")
class TestModificationEdgeCases:

    async def test_modification_targeting_observation(
        self, client, db_session, voice_fixtures,
    ):
        """modify_exercise_card targeting an observation_card → warning, not modified."""
        _, db_client, session = voice_fixtures

        from app.services import entry_service
        next_seq = await entry_service.get_next_sequence_order(db_session, session.id)

        obs_entry = SessionEntry(
            session_id=session.id,
            client_id=db_client.id,
            entry_type=EntryTypeEnum.observation_card,
            sequence_order=next_seq,
            observation_text="Client looks tired",
            flag_color="green",
            flag_reason="general observation",
        )
        db_session.add(obs_entry)
        await db_session.flush()

        existing = await entry_service.list_entries_by_session(db_session, session.id)
        target_id = len(existing)

        tool_calls = [
            _make_tool_use_block("modify_exercise_card", {
                "target_entry_id": target_id,
                "action": "add",
                "updates": {"rpe": 8},
            })
        ]

        with _patch_both(transcript="RPE 8 on that", tool_calls=tool_calls):
            response = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )

        assert response.status_code == 201
        data = response.json()["data"]
        assert len(data["entries_modified"]) == 0
        codes = [w["code"] for w in data["warnings"]]
        assert "target_not_exercise" in codes

    async def test_modification_form_notes_appended(
        self, client, db_session, voice_fixtures,
    ):
        """Modification with only form_notes → appended to existing entry."""
        _, db_client, session = voice_fixtures

        from app.services import entry_service
        next_seq = await entry_service.get_next_sequence_order(db_session, session.id)

        existing_entry = SessionEntry(
            session_id=session.id,
            client_id=db_client.id,
            entry_type=EntryTypeEnum.exercise_card,
            sequence_order=next_seq,
            exercise_name="bench press",
            sets=[{"reps": 10, "weight": 80, "weight_unit": "kg"}],
            form_notes=["Keep elbows tucked"],
        )
        db_session.add(existing_entry)
        await db_session.flush()

        existing = await entry_service.list_entries_by_session(db_session, session.id)
        target_id = len(existing)

        tool_calls = [
            _make_tool_use_block("modify_exercise_card", {
                "target_entry_id": target_id,
                "action": "add",
                "form_notes": ["Good depth on last rep"],
            })
        ]

        with _patch_both(
            transcript="good depth on last rep",
            tool_calls=tool_calls,
        ):
            response = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )

        assert response.status_code == 201
        data = response.json()["data"]
        assert len(data["entries_modified"]) == 1
        modified = data["entries_modified"][0]
        assert "Keep elbows tucked" in modified["form_notes"]
        assert "Good depth on last rep" in modified["form_notes"]

    async def test_modification_cues_appended(
        self, client, db_session, voice_fixtures,
    ):
        """Modification with only cues_given → appended to existing entry."""
        _, db_client, session = voice_fixtures

        from app.services import entry_service
        next_seq = await entry_service.get_next_sequence_order(db_session, session.id)

        existing_entry = SessionEntry(
            session_id=session.id,
            client_id=db_client.id,
            entry_type=EntryTypeEnum.exercise_card,
            sequence_order=next_seq,
            exercise_name="squat",
            sets=[{"reps": 5, "weight": 100, "weight_unit": "kg"}],
            cues_given=["Brace core"],
        )
        db_session.add(existing_entry)
        await db_session.flush()

        existing = await entry_service.list_entries_by_session(db_session, session.id)
        target_id = len(existing)

        tool_calls = [
            _make_tool_use_block("modify_exercise_card", {
                "target_entry_id": target_id,
                "action": "add",
                "cues_given": ["Squeeze at top"],
            })
        ]

        with _patch_both(transcript="squeeze at top", tool_calls=tool_calls):
            response = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )

        assert response.status_code == 201
        data = response.json()["data"]
        assert len(data["entries_modified"]) == 1
        modified = data["entries_modified"][0]
        assert "Brace core" in modified["cues_given"]
        assert "Squeeze at top" in modified["cues_given"]

    async def test_modification_target_sets_subset(
        self, client, db_session, voice_fixtures,
    ):
        """target_sets=[1] on entry with 3 sets → only set 0 updated."""
        _, db_client, session = voice_fixtures

        from app.services import entry_service
        next_seq = await entry_service.get_next_sequence_order(db_session, session.id)

        existing_entry = SessionEntry(
            session_id=session.id,
            client_id=db_client.id,
            entry_type=EntryTypeEnum.exercise_card,
            sequence_order=next_seq,
            exercise_name="deadlift",
            sets=[
                {"reps": 5, "weight": 140, "weight_unit": "kg"},
                {"reps": 5, "weight": 140, "weight_unit": "kg"},
                {"reps": 5, "weight": 140, "weight_unit": "kg"},
            ],
        )
        db_session.add(existing_entry)
        await db_session.flush()

        existing = await entry_service.list_entries_by_session(db_session, session.id)
        target_id = len(existing)

        tool_calls = [
            _make_tool_use_block("modify_exercise_card", {
                "target_entry_id": target_id,
                "action": "add",
                "target_sets": [1],
                "updates": {"rpe": 9},
            })
        ]

        with _patch_both(
            transcript="RPE 9 on the first set",
            tool_calls=tool_calls,
        ):
            response = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )

        assert response.status_code == 201
        data = response.json()["data"]
        assert len(data["entries_modified"]) == 1
        sets = data["entries_modified"][0]["sets"]
        assert sets[0]["rpe"] == 9      # set 1 (0-indexed: 0) updated
        assert "rpe" not in sets[1]     # set 2 unchanged
        assert "rpe" not in sets[2]     # set 3 unchanged

    async def test_modification_out_of_range(
        self, client, db_session, voice_fixtures,
    ):
        """target_entry_id=99 → warning, entries_modified empty."""
        _, _, session = voice_fixtures

        tool_calls = [
            _make_tool_use_block("modify_exercise_card", {
                "target_entry_id": 99,
                "action": "add",
                "updates": {"rpe": 8},
            })
        ]

        with _patch_both(transcript="RPE 8 on that", tool_calls=tool_calls):
            response = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )

        assert response.status_code == 201
        data = response.json()["data"]
        assert len(data["entries_modified"]) == 0
        codes = [w["code"] for w in data["warnings"]]
        assert "invalid_target" in codes

    async def test_modification_weight_correction(
        self, client, db_session, voice_fixtures,
    ):
        """Weight correction → DB set weight updated."""
        _, db_client, session = voice_fixtures

        from app.services import entry_service
        next_seq = await entry_service.get_next_sequence_order(db_session, session.id)

        existing_entry = SessionEntry(
            session_id=session.id,
            client_id=db_client.id,
            entry_type=EntryTypeEnum.exercise_card,
            sequence_order=next_seq,
            exercise_name="bench press",
            sets=[{"reps": 10, "weight": 80, "weight_unit": "kg"}],
        )
        db_session.add(existing_entry)
        await db_session.flush()

        existing = await entry_service.list_entries_by_session(db_session, session.id)
        target_id = len(existing)

        tool_calls = [
            _make_tool_use_block("modify_exercise_card", {
                "target_entry_id": target_id,
                "action": "correct",
                "updates": {"weight": 85, "weight_unit": "kg"},
            })
        ]

        with _patch_both(
            transcript="actually that was 85 kilos",
            tool_calls=tool_calls,
        ):
            response = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )

        assert response.status_code == 201
        data = response.json()["data"]
        assert len(data["entries_modified"]) == 1
        s = data["entries_modified"][0]["sets"][0]
        assert s["weight"] == 85.0
        assert s["weight_original"] == 85


# ===================================================================
# Step 4: Mixed Content Clips
# ===================================================================


@pytest.mark.asyncio(loop_scope="session")
class TestMixedContentClips:

    async def test_exercise_plus_observation_same_clip(
        self, client, voice_fixtures,
    ):
        """record_exercise_card + record_observation_card in one clip → both created."""
        _, _, session = voice_fixtures
        tool_calls = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "overhead press",
                "sets": [{"reps": 8, "weight": 40, "weight_unit": "kg"}],
            }),
            _make_tool_use_block("record_observation_card", {
                "observation_text": "Right shoulder clicking during press",
                "flag_color": "red",
                "flag_reason": "joint noise",
            }),
        ]

        with _patch_both(
            transcript="overhead press 8 at 40, shoulder clicking",
            tool_calls=tool_calls,
        ):
            response = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )

        assert response.status_code == 201
        data = response.json()["data"]
        assert len(data["entries_created"]) == 2
        types = [e["entry_type"] for e in data["entries_created"]]
        assert "exercise_card" in types
        assert "observation_card" in types

    async def test_exercise_plus_clarification_same_clip(
        self, client, voice_fixtures,
    ):
        """record_exercise_card + yellow observation → exercise persisted, yellow in clarifications."""
        _, _, session = voice_fixtures
        tool_calls = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "lat pulldown",
                "sets": [{"reps": 12, "weight": 50, "weight_unit": "kg"}],
            }),
            _make_tool_use_block("record_observation_card", {
                "observation_text": "Did you say 50 or 15 kilos?",
                "flag_color": "yellow",
                "flag_reason": "ambiguous weight",
            }),
        ]

        with _patch_both(
            transcript="lat pulldown twelve at fifty, wait was that fifty?",
            tool_calls=tool_calls,
        ):
            response = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )

        assert response.status_code == 201
        data = response.json()["data"]
        # Exercise persisted, yellow observation NOT persisted
        assert len(data["entries_created"]) == 1
        assert data["entries_created"][0]["entry_type"] == "exercise_card"
        assert len(data["clarifications_needed"]) == 1
        assert data["clarifications_needed"][0]["flag_reason"] == "ambiguous weight"

    async def test_exercise_plus_modification_same_clip(
        self, client, db_session, voice_fixtures,
    ):
        """New exercise + modify existing → new entry created AND existing modified."""
        _, db_client, session = voice_fixtures

        from app.services import entry_service
        next_seq = await entry_service.get_next_sequence_order(db_session, session.id)

        # Pre-existing entry to modify
        existing_entry = SessionEntry(
            session_id=session.id,
            client_id=db_client.id,
            entry_type=EntryTypeEnum.exercise_card,
            sequence_order=next_seq,
            exercise_name="squat",
            sets=[{"reps": 5, "weight": 120, "weight_unit": "kg"}],
        )
        db_session.add(existing_entry)
        await db_session.flush()

        existing = await entry_service.list_entries_by_session(db_session, session.id)
        target_id = len(existing)

        tool_calls = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "leg curl",
                "sets": [{"reps": 12, "weight": 30, "weight_unit": "kg"}],
            }),
            _make_tool_use_block("modify_exercise_card", {
                "target_entry_id": target_id,
                "action": "add",
                "updates": {"rpe": 7},
            }),
        ]

        with _patch_both(
            transcript="leg curl twelve at 30, oh and RPE 7 on those squats",
            tool_calls=tool_calls,
        ):
            response = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )

        assert response.status_code == 201
        data = response.json()["data"]
        assert len(data["entries_created"]) == 1
        assert data["entries_created"][0]["exercise_name"] == "leg curl"
        assert len(data["entries_modified"]) == 1
        assert data["entries_modified"][0]["sets"][0]["rpe"] == 7


# ===================================================================
# Step 5: Data Integrity
# ===================================================================


@pytest.mark.asyncio(loop_scope="session")
class TestDataIntegrity:

    async def test_sequence_order_increments(self, client, voice_fixtures):
        """Two exercise cards in one clip → sequence_order values are consecutive."""
        _, _, session = voice_fixtures
        tool_calls = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "cable row",
                "sets": [{"reps": 12, "weight": 40, "weight_unit": "kg"}],
            }),
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "face pull",
                "sets": [{"reps": 15, "weight": 15, "weight_unit": "kg"}],
            }),
        ]

        with _patch_both(
            transcript="cable row twelve at 40, face pull fifteen at 15",
            tool_calls=tool_calls,
        ):
            response = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )

        assert response.status_code == 201
        entries = response.json()["data"]["entries_created"]
        assert len(entries) == 2
        seq_orders = [e["sequence_order"] for e in entries]
        assert seq_orders[1] == seq_orders[0] + 1

    async def test_total_volume_computed(self, client, voice_fixtures):
        """3 sets × 10 reps × 80kg → total_volume_kg = 2400.0."""
        _, _, session = voice_fixtures
        tool_calls = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "bench press",
                "sets": [
                    {"reps": 10, "weight": 80, "weight_unit": "kg"},
                    {"reps": 10, "weight": 80, "weight_unit": "kg"},
                    {"reps": 10, "weight": 80, "weight_unit": "kg"},
                ],
            })
        ]

        with _patch_both(
            transcript="bench press three sets of ten at 80",
            tool_calls=tool_calls,
        ):
            response = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )

        assert response.status_code == 201
        entry = response.json()["data"]["entries_created"][0]
        assert entry["total_volume_kg"] == 2400.0

    async def test_exercise_canonical_set_on_exact_match(
        self, client, voice_fixtures,
    ):
        """Full exercise name → exercise_canonical set via exact match."""
        _, _, session = voice_fixtures
        tool_calls = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "barbell bench press",
                "sets": [{"reps": 8, "weight": 60, "weight_unit": "kg"}],
            })
        ]

        with _patch_both(
            transcript="barbell bench press eight at 60",
            tool_calls=tool_calls,
        ):
            response = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )

        assert response.status_code == 201
        entry = response.json()["data"]["entries_created"][0]
        assert entry["exercise_canonical"] is not None
        assert entry["exercise_canonical"].lower() == "barbell bench press"

    async def test_rir_persisted_through_pipeline(self, client, voice_fixtures):
        """RIR flows through parser → validation (→ RPE derivation) → DB."""
        _, _, session = voice_fixtures
        tool_calls = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "squat",
                "sets": [{"reps": 5, "weight": 100, "weight_unit": "kg", "rir": 2}],
            }),
        ]

        with _patch_both(
            transcript="squat 5 at 100 RIR 2",
            tool_calls=tool_calls,
        ):
            response = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )

        assert response.status_code == 201
        entry = response.json()["data"]["entries_created"][0]
        stored_set = entry["sets"][0]
        assert stored_set["rir"] == 2
        assert stored_set["rpe"] == 8.0  # RIR 2 → RPE 8

    async def test_equipment_note_persisted_through_pipeline(self, client, voice_fixtures):
        """Equipment note flows through parser → validation → DB."""
        _, _, session = voice_fixtures
        tool_calls = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "squat",
                "sets": [{"reps": 10, "weight": 60, "weight_unit": "kg", "equipment_note": "with a red band"}],
            }),
        ]

        with _patch_both(
            transcript="squat 10 at 60 with a red band",
            tool_calls=tool_calls,
        ):
            response = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )

        assert response.status_code == 201
        entry = response.json()["data"]["entries_created"][0]
        stored_set = entry["sets"][0]
        assert stored_set["equipment_note"] == "with a red band"

    async def test_rir_and_equipment_together_full_pipeline(
        self, client, voice_fixtures,
    ):
        """RIR + equipment_note on same set → both persist through pipeline."""
        _, _, session = voice_fixtures
        tool_calls = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "squat",
                "sets": [
                    {"reps": 10, "weight": 60, "weight_unit": "kg", "rir": 3, "equipment_note": "with a band"},
                ],
            }),
        ]

        with _patch_both(
            transcript="squat 10 at 60 with a band, RIR 3",
            tool_calls=tool_calls,
        ):
            response = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )

        assert response.status_code == 201
        entry = response.json()["data"]["entries_created"][0]
        stored_set = entry["sets"][0]
        assert stored_set["rir"] == 3
        assert stored_set["rpe"] == 7.0  # RIR 3 → RPE 7
        assert stored_set["equipment_note"] == "with a band"

    async def test_modification_with_rir_derives_rpe_in_pipeline(
        self, client, voice_fixtures,
    ):
        """Modification with rir → validation derives RPE → verify in modified entry."""
        _, _, session = voice_fixtures

        # First, create an exercise entry via the pipeline
        exercise_tool = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "bench press",
                "sets": [{"reps": 10, "weight": 80, "weight_unit": "kg"}],
            }),
        ]

        with _patch_both(
            transcript="bench press 10 at 80",
            tool_calls=exercise_tool,
        ):
            create_resp = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )
        assert create_resp.status_code == 201

        # Now send a modification with RIR — pipeline loads existing entries from DB
        mod_tool = [
            _make_tool_use_block("modify_exercise_card", {
                "target_entry_id": 1,
                "action": "add",
                "updates": {"rir": 2},
            }),
        ]

        with _patch_both(
            transcript="RIR 2 on those",
            tool_calls=mod_tool,
        ):
            mod_resp = await client.post(
                f"/api/v1/sessions/{session.id}/voice-clip",
                files={"audio": ("test.wav", b"fake-audio-data", "audio/wav")},
            )

        assert mod_resp.status_code == 201
        mod_data = mod_resp.json()["data"]
        # The entry was modified in-place — check entries_modified
        assert len(mod_data["entries_modified"]) == 1
        modified_entry = mod_data["entries_modified"][0]
        stored_set = modified_entry["sets"][0]
        assert stored_set["rir"] == 2
        assert stored_set["rpe"] == 8.0  # RIR 2 → RPE 8
