"""Voice clip and text entry processing endpoints.

Receives audio via file upload or typed text via JSON, runs the full
pipeline (Deepgram → Claude parser → validation → persist for audio,
Claude parser → validation → persist for text), and returns structured
timeline cards.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import validate_session_ownership
from app.database import get_db
from app.schemas import (
    ClarificationItem as ClarificationSchema,
    DataResponse,
    SessionEntryResponse,
    TextEntryRequest,
    TimingBreakdownResponse,
    TranscribeResponse,
    ValidationWarningResponse,
    VoiceClipResponse,
)
from app.services import client_service, voice as voice_service
from app.services.transcription import transcribe_audio
from app.services.voice import VoiceClipResult

# 25 MB — generous for voice clips (1 min WAV ≈ 10 MB, compressed ≈ 1 MB)
MAX_AUDIO_SIZE_BYTES = 25 * 1024 * 1024

ALLOWED_AUDIO_TYPES = {
    "audio/wav",
    "audio/wave",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "audio/webm",
    "audio/ogg",
    "audio/flac",
    "audio/aac",
    "audio/amr",
    "audio/3gpp",
    # Some clients send generic binary type
    "application/octet-stream",
}

router = APIRouter(tags=["voice"])


def _build_voice_response(result: VoiceClipResult) -> dict:
    """Build the standard API response dict from a VoiceClipResult."""
    total_ms = (
        result.transcription_ms + result.parsing_ms
        + result.validation_ms + result.persistence_ms
    )

    response = VoiceClipResponse(
        entries_created=[SessionEntryResponse.model_validate(e) for e in result.entries_created],
        entries_modified=[SessionEntryResponse.model_validate(e) for e in result.entries_modified],
        clarifications_needed=[
            ClarificationSchema(
                observation_text=c.observation_text,
                flag_reason=c.flag_reason,
            )
            for c in result.clarifications
        ],
        warnings=[
            ValidationWarningResponse(
                field=w.field,
                code=w.code,
                message=w.message,
            )
            for w in result.warnings
        ],
        transcript=result.transcript,
        confidence=result.confidence,
        timing=TimingBreakdownResponse(
            transcription_ms=result.transcription_ms,
            parsing_ms=result.parsing_ms,
            validation_ms=result.validation_ms,
            persistence_ms=result.persistence_ms,
            total_ms=total_ms,
        ),
    )

    return {"data": response, "meta": {}}


@router.post(
    "/sessions/{session_id}/voice-clip",
    response_model=DataResponse[VoiceClipResponse],
    status_code=201,
)
async def process_voice_clip(
    session_id: uuid.UUID,
    audio: UploadFile,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Process a voice clip and return structured timeline cards.

    Receives audio via multipart/form-data, transcribes it, parses the
    transcript into exercise/observation cards, validates and normalizes
    the data, persists to DB, and returns the result with timing breakdown.
    """
    session = await validate_session_ownership(db, session_id)

    # Validate MIME type
    mime_type = audio.content_type or "audio/wav"
    if mime_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported audio type: {mime_type}",
        )

    # Read and validate audio (size-limited to prevent memory exhaustion)
    audio_data = await audio.read(MAX_AUDIO_SIZE_BYTES + 1)
    if not audio_data:
        raise HTTPException(status_code=422, detail="Audio file is empty")
    if len(audio_data) > MAX_AUDIO_SIZE_BYTES:
        raise HTTPException(
            status_code=422,
            detail=f"Audio file too large. Maximum size is {MAX_AUDIO_SIZE_BYTES // (1024 * 1024)} MB.",
        )

    # Load client's preferred weight unit
    client = await client_service.get_client(db, session.client_id)
    default_weight_unit = (client.preferred_weight_unit or "kg") if client else "kg"

    # Run the pipeline
    result = await voice_service.process_voice_clip(
        db=db,
        session_id=session_id,
        client_id=session.client_id,
        audio_data=audio_data,
        mime_type=mime_type,
        default_weight_unit=default_weight_unit,
    )

    return _build_voice_response(result)


@router.post(
    "/sessions/{session_id}/text-entry",
    response_model=DataResponse[VoiceClipResponse],
    status_code=201,
)
async def process_text_entry(
    session_id: uuid.UUID,
    body: TextEntryRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Process typed text through the parser pipeline.

    Same output format as voice-clip — the text goes through
    Claude parser → validation → persistence, skipping transcription.
    Used when the trainer types an entry after a clarification prompt.
    """
    session = await validate_session_ownership(db, session_id)

    client = await client_service.get_client(db, session.client_id)
    default_weight_unit = (client.preferred_weight_unit or "kg") if client else "kg"

    result = await voice_service.process_text_entry(
        db=db,
        session_id=session_id,
        client_id=session.client_id,
        text=body.text,
        default_weight_unit=default_weight_unit,
    )

    return _build_voice_response(result)


@router.post(
    "/transcribe",
    response_model=DataResponse[TranscribeResponse],
    status_code=200,
)
async def transcribe(audio: UploadFile) -> dict:
    """Transcribe audio and return raw text — no parsing or persistence.

    Used for plan dictation: trainer speaks notes, we return the text
    so they can edit before saving.
    """
    mime_type = audio.content_type or "audio/wav"
    if mime_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported audio type: {mime_type}",
        )

    audio_data = await audio.read(MAX_AUDIO_SIZE_BYTES + 1)
    if not audio_data:
        raise HTTPException(status_code=422, detail="Audio file is empty")
    if len(audio_data) > MAX_AUDIO_SIZE_BYTES:
        raise HTTPException(
            status_code=422,
            detail=f"Audio file too large. Maximum size is {MAX_AUDIO_SIZE_BYTES // (1024 * 1024)} MB.",
        )

    result = await transcribe_audio(audio_data, mime_type=mime_type)

    return {
        "data": TranscribeResponse(
            transcript=result.transcript,
            confidence=result.confidence,
        ),
        "meta": {},
    }
