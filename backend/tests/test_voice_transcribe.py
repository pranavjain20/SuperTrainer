"""Tests for the transcribe-only endpoint (POST /api/v1/transcribe).

Mocks Deepgram — we test the endpoint's validation and response shape,
not the STT service itself (that's covered in test_transcription.py).
"""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def _mock_deepgram():
    """Patch transcribe_audio to return a controlled result."""
    from app.services.transcription import TranscriptionResult

    result = TranscriptionResult(
        transcript="bench press three sets of eight",
        confidence=0.95,
        duration_seconds=4.2,
    )
    with patch(
        "app.api.voice.transcribe_audio",
        new_callable=AsyncMock,
        return_value=result,
    ) as mock:
        yield mock


@pytest.fixture
def _mock_deepgram_empty():
    """Patch transcribe_audio to return an empty transcript (silence)."""
    from app.services.transcription import TranscriptionResult

    result = TranscriptionResult(
        transcript="",
        confidence=0.0,
        duration_seconds=2.0,
    )
    with patch(
        "app.api.voice.transcribe_audio",
        new_callable=AsyncMock,
        return_value=result,
    ) as mock:
        yield mock


AUDIO_BYTES = b"\x00\x01\x02\x03" * 100  # Fake audio data


class TestTranscribeEndpoint:
    """POST /api/v1/transcribe"""

    @pytest.mark.asyncio(loop_scope="session")
    @pytest.mark.usefixtures("_mock_deepgram")
    async def test_happy_path(self, client):
        resp = await client.post(
            "/api/v1/transcribe",
            files={"audio": ("recording.m4a", AUDIO_BYTES, "audio/mp4")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["transcript"] == "bench press three sets of eight"
        assert body["data"]["confidence"] == 0.95

    @pytest.mark.asyncio(loop_scope="session")
    async def test_empty_audio_returns_422(self, client):
        resp = await client.post(
            "/api/v1/transcribe",
            files={"audio": ("recording.m4a", b"", "audio/mp4")},
        )
        assert resp.status_code == 422
        assert "empty" in resp.json()["error"]["message"].lower()

    @pytest.mark.asyncio(loop_scope="session")
    async def test_bad_mime_type_returns_422(self, client):
        resp = await client.post(
            "/api/v1/transcribe",
            files={"audio": ("notes.txt", AUDIO_BYTES, "text/plain")},
        )
        assert resp.status_code == 422
        assert "Unsupported audio type" in resp.json()["error"]["message"]

    @pytest.mark.asyncio(loop_scope="session")
    async def test_file_too_large_returns_422(self, client):
        # 25 MB limit — send 25 MB + 1 byte
        oversized = b"\x00" * (25 * 1024 * 1024 + 1)
        resp = await client.post(
            "/api/v1/transcribe",
            files={"audio": ("huge.m4a", oversized, "audio/mp4")},
        )
        assert resp.status_code == 422
        assert "too large" in resp.json()["error"]["message"].lower()

    @pytest.mark.asyncio(loop_scope="session")
    @pytest.mark.usefixtures("_mock_deepgram_empty")
    async def test_silence_returns_empty_transcript(self, client):
        resp = await client.post(
            "/api/v1/transcribe",
            files={"audio": ("recording.m4a", AUDIO_BYTES, "audio/mp4")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["transcript"] == ""
        assert body["data"]["confidence"] == 0.0
