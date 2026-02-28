"""Tests for the transcription service — exercise DB loading, keyterm
building, and Deepgram audio transcription (mocked)."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.transcription import (
    GYM_TERMS,
    KEYTERM_LIMIT,
    TranscriptionResult,
    WordInfo,
    build_keyterm_list,
    load_exercise_db,
    transcribe_audio,
)


# ===================================================================
# load_exercise_db
# ===================================================================


class TestLoadExerciseDb:
    """Tests for loading and validating the exercise database JSON."""

    def test_returns_list(self):
        result = load_exercise_db()
        assert isinstance(result, list)

    def test_not_empty(self):
        result = load_exercise_db()
        assert len(result) > 0

    def test_every_exercise_has_required_fields(self):
        required = {"canonical_name", "aliases", "category", "primary_muscles", "equipment", "difficulty"}
        exercises = load_exercise_db()
        for exercise in exercises:
            missing = required - set(exercise.keys())
            assert not missing, (
                f"{exercise.get('canonical_name', 'UNKNOWN')} missing fields: {missing}"
            )

    def test_no_duplicate_canonical_names(self):
        exercises = load_exercise_db()
        names = [e["canonical_name"] for e in exercises]
        duplicates = [n for n in names if names.count(n) > 1]
        assert not duplicates, f"Duplicate canonical names: {set(duplicates)}"

    def test_aliases_are_lists_of_strings(self):
        exercises = load_exercise_db()
        for exercise in exercises:
            aliases = exercise["aliases"]
            assert isinstance(aliases, list), (
                f"{exercise['canonical_name']}: aliases should be a list"
            )
            for alias in aliases:
                assert isinstance(alias, str), (
                    f"{exercise['canonical_name']}: alias {alias!r} is not a string"
                )

    def test_file_not_found_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_exercise_db(tmp_path / "nonexistent.json")

    def test_preserves_original_exercises(self):
        """The 19 original seed exercises must still exist in the database.

        Four canonical names changed in the batch-file rebuild:
        Deadlift → Conventional Deadlift, Lunges → Walking Lunge,
        Step-Ups → Step Up, Seated Row → Seated Cable Row.
        """
        original_names = {
            "Barbell Back Squat", "Barbell Bench Press", "Conventional Deadlift",
            "Overhead Press", "Barbell Row", "Goblet Squat", "Front Squat",
            "Leg Press", "Lat Pulldown", "Seated Cable Row", "Pull-Up",
            "Romanian Deadlift", "Walking Lunge", "Step Up", "Lateral Raise",
            "Dead Bug", "Plank", "Bird Dog", "Band Pull-Apart",
        }
        exercises = load_exercise_db()
        db_names = {e["canonical_name"] for e in exercises}
        missing = original_names - db_names
        assert not missing, f"Original exercises missing from DB: {missing}"


# ===================================================================
# build_keyterm_list
# ===================================================================


class TestBuildKeytermList:
    """Tests for building the Deepgram keyterm list from exercise data."""

    def test_returns_list_of_strings(self):
        result = build_keyterm_list()
        assert isinstance(result, list)
        assert all(isinstance(t, str) for t in result)

    def test_capped_at_100(self):
        result = build_keyterm_list()
        assert len(result) <= KEYTERM_LIMIT

    def test_no_duplicates(self):
        result = build_keyterm_list()
        lowered = [t.lower() for t in result]
        assert len(lowered) == len(set(lowered))

    def test_includes_multi_word_canonical_names(self):
        """At least some multi-word exercise names should appear in keyterms."""
        exercises = load_exercise_db()
        result = build_keyterm_list(exercises)
        result_lower = {t.lower() for t in result}

        multi_word_canonicals = {
            e["canonical_name"].lower()
            for e in exercises
            if " " in e["canonical_name"] or "-" in e["canonical_name"]
        }
        overlap = multi_word_canonicals & result_lower
        assert len(overlap) > 0, "No multi-word canonical names in keyterm list"

    def test_includes_abbreviations(self):
        """Common abbreviations like RDL and OHP should appear."""
        exercises = load_exercise_db()
        result = build_keyterm_list(exercises)
        result_set = set(result)
        # At least some abbreviations should be present
        abbreviations_found = [t for t in result_set if t.isupper() and len(t) <= 6]
        assert len(abbreviations_found) > 0, "No abbreviations found in keyterm list"

    def test_includes_gym_terms(self):
        """Gym jargon (RPE, AMRAP, etc.) should be included."""
        result = build_keyterm_list()
        result_set = set(result)
        # At least some gym terms should be present (they might get
        # pushed out if there are 100+ exercise terms, but RPE/AMRAP
        # are high priority)
        assert "RPE" in result_set or "AMRAP" in result_set

    def test_skips_common_single_words(self):
        """Common single English words like 'squat' should be excluded."""
        result = build_keyterm_list()
        result_lower = {t.lower() for t in result}
        assert "squat" not in result_lower
        assert "bench" not in result_lower
        assert "plank" not in result_lower

    def test_accepts_custom_exercise_list(self):
        """Should work with a custom exercise list, not just the default file."""
        custom = [
            {
                "canonical_name": "Zercher Squat",
                "aliases": ["zercher", "ZS"],
                "category": "compound",
                "primary_muscles": ["quadriceps"],
                "equipment": ["barbell"],
                "difficulty": "advanced",
            },
        ]
        result = build_keyterm_list(custom)
        assert isinstance(result, list)
        assert "Zercher Squat" in result

    def test_handles_empty_aliases(self):
        """Exercises with empty or missing aliases should not break keyterm building."""
        custom = [
            {
                "canonical_name": "Machine Leg Press",
                "aliases": [],
                "category": "compound",
                "primary_muscles": ["quadriceps"],
                "equipment": ["machine"],
                "difficulty": "beginner",
            },
            {
                "canonical_name": "Cable Fly",
                "category": "isolation",
                "primary_muscles": ["chest"],
                "equipment": ["cable"],
                "difficulty": "beginner",
            },
        ]
        result = build_keyterm_list(custom)
        assert "Machine Leg Press" in result
        assert "Cable Fly" in result


# ===================================================================
# transcribe_audio
# ===================================================================


def _make_mock_response(
    transcript: str = "five sets of squats at 80 kilos",
    confidence: float = 0.95,
    duration: float = 4.2,
    words: list[dict] | None = None,
) -> MagicMock:
    """Build a mock Deepgram PrerecordedResponse."""
    if words is None:
        words = [
            {"word": "five", "start": 0.0, "end": 0.3, "confidence": 0.98},
            {"word": "sets", "start": 0.3, "end": 0.6, "confidence": 0.97},
            {"word": "of", "start": 0.6, "end": 0.7, "confidence": 0.99},
            {"word": "squats", "start": 0.7, "end": 1.1, "confidence": 0.96},
            {"word": "at", "start": 1.1, "end": 1.2, "confidence": 0.99},
            {"word": "80", "start": 1.2, "end": 1.5, "confidence": 0.94},
            {"word": "kilos", "start": 1.5, "end": 1.9, "confidence": 0.93},
        ]

    mock_words = []
    for w in words:
        mock_word = MagicMock()
        mock_word.word = w["word"]
        mock_word.start = w["start"]
        mock_word.end = w["end"]
        mock_word.confidence = w["confidence"]
        mock_words.append(mock_word)

    mock_alternative = MagicMock()
    mock_alternative.transcript = transcript
    mock_alternative.confidence = confidence
    mock_alternative.words = mock_words

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


@pytest.mark.asyncio(loop_scope="session")
class TestTranscribeAudio:
    """Tests for the Deepgram transcription wrapper."""

    async def test_rejects_empty_bytes(self):
        with pytest.raises(ValueError, match="must not be empty"):
            await transcribe_audio(b"")

    @patch("app.services.transcription.DeepgramClient")
    async def test_returns_transcription_result(self, mock_client_cls):
        mock_response = _make_mock_response()
        mock_async_rest = AsyncMock()
        mock_async_rest.transcribe_file.return_value = mock_response
        mock_client_cls.return_value.listen.asyncrest.v.return_value = mock_async_rest

        result = await transcribe_audio(b"fake-audio-bytes", keyterms=["squat"])

        assert isinstance(result, TranscriptionResult)
        assert result.transcript == "five sets of squats at 80 kilos"
        assert result.confidence == 0.95
        assert result.duration_seconds == 4.2

    @patch("app.services.transcription.DeepgramClient")
    async def test_extracts_word_level_data(self, mock_client_cls):
        mock_response = _make_mock_response()
        mock_async_rest = AsyncMock()
        mock_async_rest.transcribe_file.return_value = mock_response
        mock_client_cls.return_value.listen.asyncrest.v.return_value = mock_async_rest

        result = await transcribe_audio(b"fake-audio-bytes", keyterms=["squat"])

        assert len(result.words) == 7
        first_word = result.words[0]
        assert isinstance(first_word, WordInfo)
        assert first_word.word == "five"
        assert first_word.start == 0.0
        assert first_word.end == 0.3
        assert first_word.confidence == 0.98

    @patch("app.services.transcription.DeepgramClient")
    async def test_uses_nova3_model(self, mock_client_cls):
        mock_response = _make_mock_response()
        mock_async_rest = AsyncMock()
        mock_async_rest.transcribe_file.return_value = mock_response
        mock_client_cls.return_value.listen.asyncrest.v.return_value = mock_async_rest

        await transcribe_audio(b"fake-audio-bytes", keyterms=[])

        # Verify PrerecordedOptions passed to transcribe_file
        call_args = mock_async_rest.transcribe_file.call_args
        options = call_args.kwargs.get("options") or call_args[1].get("options")
        assert options.model == "nova-3"

    @patch("app.services.transcription.DeepgramClient")
    async def test_passes_keyterms_to_api(self, mock_client_cls):
        mock_response = _make_mock_response()
        mock_async_rest = AsyncMock()
        mock_async_rest.transcribe_file.return_value = mock_response
        mock_client_cls.return_value.listen.asyncrest.v.return_value = mock_async_rest

        keyterms = ["Romanian Deadlift", "RDL", "RPE"]
        await transcribe_audio(b"fake-audio-bytes", keyterms=keyterms)

        call_args = mock_async_rest.transcribe_file.call_args
        options = call_args.kwargs.get("options") or call_args[1].get("options")
        assert options.keyterm == keyterms

    @patch("app.services.transcription.DeepgramClient")
    async def test_handles_empty_transcript(self, mock_client_cls):
        """Silence / no speech should return empty transcript, not error."""
        mock_response = _make_mock_response(
            transcript="",
            confidence=0.0,
            duration=3.0,
            words=[],
        )
        mock_async_rest = AsyncMock()
        mock_async_rest.transcribe_file.return_value = mock_response
        mock_client_cls.return_value.listen.asyncrest.v.return_value = mock_async_rest

        result = await transcribe_audio(b"fake-silence-bytes", keyterms=[])

        assert result.transcript == ""
        assert result.confidence == 0.0
        assert result.duration_seconds == 3.0
        assert result.words == ()

    @patch("app.services.transcription.DeepgramClient")
    async def test_passes_mime_type(self, mock_client_cls):
        mock_response = _make_mock_response()
        mock_async_rest = AsyncMock()
        mock_async_rest.transcribe_file.return_value = mock_response
        mock_client_cls.return_value.listen.asyncrest.v.return_value = mock_async_rest

        await transcribe_audio(
            b"fake-audio-bytes",
            mime_type="audio/webm",
            keyterms=[],
        )

        call_args = mock_async_rest.transcribe_file.call_args
        source = call_args[0][0]
        assert source["mimetype"] == "audio/webm"

    @patch("app.services.transcription.DeepgramClient")
    async def test_handles_empty_channels(self, mock_client_cls):
        """Deepgram returning empty channels should give empty result, not crash."""
        mock_results = MagicMock()
        mock_results.channels = []
        mock_metadata = MagicMock()
        mock_metadata.duration = 2.5
        mock_response = MagicMock()
        mock_response.results = mock_results
        mock_response.metadata = mock_metadata

        mock_async_rest = AsyncMock()
        mock_async_rest.transcribe_file.return_value = mock_response
        mock_client_cls.return_value.listen.asyncrest.v.return_value = mock_async_rest

        result = await transcribe_audio(b"fake-audio-bytes", keyterms=[])

        assert result.transcript == ""
        assert result.confidence == 0.0
        assert result.duration_seconds == 2.5
        assert result.words == ()
