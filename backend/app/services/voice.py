"""Voice clip orchestration service.

Wires together Deepgram transcription → Claude parser → validation layer
into a single pipeline. Handles persistence of results to DB.

Separated from the router so pipeline logic is testable independently
of HTTP concerns.
"""

import logging
import time
import uuid
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("supertrainer")

from app.models import EntryTypeEnum, SessionEntry
from app.services import entry_service
from app.services.parser import parse_transcript
from app.services.transcription import transcribe_audio
from app.services.validation import (
    ValidationWarning,
    ValidatedExerciseCard,
    ValidatedModification,
    ValidatedObservationCard,
    ValidatedSet,
    validate_parser_result,
)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ClarificationItem:
    """A yellow-flagged observation that needs trainer clarification."""

    observation_text: str
    flag_reason: str | None = None


@dataclass(frozen=True)
class VoiceClipResult:
    """Complete result from processing a voice clip."""

    entries_created: tuple[SessionEntry, ...] = field(default_factory=tuple)
    entries_modified: tuple[SessionEntry, ...] = field(default_factory=tuple)
    clarifications: tuple[ClarificationItem, ...] = field(default_factory=tuple)
    warnings: tuple[ValidationWarning, ...] = field(default_factory=tuple)
    transcript: str = ""
    confidence: float = 0.0
    transcription_ms: int = 0
    parsing_ms: int = 0
    validation_ms: int = 0
    persistence_ms: int = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entry_to_context_dict(entry: SessionEntry) -> dict:
    """Convert a SessionEntry ORM object to a dict for parser context."""
    d: dict = {
        "entry_type": entry.entry_type.value,
    }
    if entry.entry_type == EntryTypeEnum.exercise_card:
        d["exercise_name"] = entry.exercise_name
        if entry.sets:
            d["sets"] = entry.sets
        if entry.form_notes:
            d["form_notes"] = list(entry.form_notes)
        if entry.cues_given:
            d["cues_given"] = list(entry.cues_given)
    elif entry.entry_type == EntryTypeEnum.observation_card:
        d["observation_text"] = entry.observation_text or ""
        if entry.attached_to_set is not None:
            d["attached_to_set"] = entry.attached_to_set
        if entry.flag_color:
            d["flag_color"] = entry.flag_color
        if entry.flag_reason:
            d["flag_reason"] = entry.flag_reason
    return d


def _validated_set_to_db_format(s: ValidatedSet) -> dict:
    """Convert a ValidatedSet to the JSONB format stored in session_entries.sets."""
    d: dict = {"reps": s.reps}
    if s.weight_kg is not None:
        d["weight"] = s.weight_kg
        d["weight_unit"] = "kg"
    if s.weight_original is not None:
        d["weight_original"] = s.weight_original
    if s.weight_unit_original is not None:
        d["weight_unit_original"] = s.weight_unit_original
    if s.rpe is not None:
        d["rpe"] = s.rpe
    if s.duration_seconds is not None:
        d["duration_seconds"] = s.duration_seconds
    if s.rir is not None:
        d["rir"] = s.rir
    if s.equipment_note is not None:
        d["equipment_note"] = s.equipment_note
    return d


def _validated_sets_to_db_format(
    sets: tuple[ValidatedSet, ...] | None,
) -> list[dict] | None:
    """Convert a tuple of ValidatedSets to DB JSONB format."""
    if sets is None:
        return None
    return [_validated_set_to_db_format(s) for s in sets]


async def _persist_exercise_card(
    db: AsyncSession,
    card: ValidatedExerciseCard,
    session_id: uuid.UUID,
    client_id: uuid.UUID,
    sequence_order: int,
) -> SessionEntry:
    """Create a DB entry from a validated exercise card."""
    return await entry_service.create_entry(
        db,
        session_id=session_id,
        client_id=client_id,
        entry_type=EntryTypeEnum.exercise_card,
        sequence_order=sequence_order,
        exercise_name=card.exercise_name,
        exercise_canonical=card.exercise_match.canonical_name if card.exercise_match else None,
        sets=_validated_sets_to_db_format(card.sets),
        total_volume_kg=card.total_volume_kg,
        form_notes=list(card.form_notes) if card.form_notes else None,
        cues_given=list(card.cues_given) if card.cues_given else None,
    )


async def _persist_observation_card(
    db: AsyncSession,
    card: ValidatedObservationCard,
    session_id: uuid.UUID,
    client_id: uuid.UUID,
    sequence_order: int,
) -> SessionEntry:
    """Create a DB entry from a validated observation card."""
    return await entry_service.create_entry(
        db,
        session_id=session_id,
        client_id=client_id,
        entry_type=EntryTypeEnum.observation_card,
        sequence_order=sequence_order,
        observation_text=card.observation_text,
        flag_color=card.flag_color,
        flag_reason=card.flag_reason,
        attached_to_set=card.attached_to_set,
    )


def _build_modification_kwargs(
    existing_entry: SessionEntry,
    mod: ValidatedModification,
) -> dict:
    """Compute the update kwargs for applying a modification to an entry.

    Set-level updates in mod.updates are applied to targeted sets. Exercise-level
    fields (form_notes, cues_given) are always appended regardless of action type.
    """
    kwargs: dict = {}

    # Handle set-level updates
    if mod.updates and existing_entry.sets:
        existing_sets = list(existing_entry.sets)

        if mod.target_sets:
            # 1-indexed → 0-indexed, skip out-of-range
            target_indices = [
                i - 1 for i in mod.target_sets
                if 1 <= i <= len(existing_sets)
            ]
        else:
            target_indices = list(range(len(existing_sets)))

        for idx in target_indices:
            s = dict(existing_sets[idx])
            for key, value in mod.updates.items():
                if key in ("weight_kg", "weight_original", "weight_unit_original"):
                    # Weight was normalized by validation — map to DB format
                    if key == "weight_kg":
                        s["weight"] = value
                        s["weight_unit"] = "kg"
                    elif key == "weight_original":
                        s["weight_original"] = value
                    elif key == "weight_unit_original":
                        s["weight_unit_original"] = value
                elif key in ("weight", "weight_unit"):
                    # Skip raw weight keys — normalized versions above handle these
                    continue
                else:
                    s[key] = value
            existing_sets[idx] = s

        kwargs["sets"] = existing_sets

    # Handle form_notes — always append (even for "correct")
    if mod.form_notes:
        existing_notes = list(existing_entry.form_notes or [])
        existing_notes.extend(mod.form_notes)
        kwargs["form_notes"] = existing_notes

    # Handle cues_given — always append
    if mod.cues_given:
        existing_cues = list(existing_entry.cues_given or [])
        existing_cues.extend(mod.cues_given)
        kwargs["cues_given"] = existing_cues

    return kwargs


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


async def process_voice_clip(
    db: AsyncSession,
    session_id: uuid.UUID,
    client_id: uuid.UUID,
    audio_data: bytes,
    mime_type: str,
    default_weight_unit: str = "kg",
) -> VoiceClipResult:
    """Process a voice clip through the full pipeline.

    Steps:
    1. Transcribe audio via Deepgram
    2. Load existing session entries for parser context
    3. Parse transcript via Claude
    4. Validate parser output (fuzzy match, weight normalization, etc.)
    5. Persist results to DB

    Args:
        db: Database session.
        session_id: The session this clip belongs to.
        client_id: The client being trained.
        audio_data: Raw audio bytes.
        mime_type: MIME type of the audio.
        default_weight_unit: Default weight unit for this client.

    Returns:
        VoiceClipResult with created/modified entries, clarifications, and timing.
    """
    all_warnings: list[ValidationWarning] = []

    # Step 1: Transcribe
    t0 = time.perf_counter()
    try:
        transcription = await transcribe_audio(audio_data, mime_type=mime_type)
    except Exception:
        logger.exception("Deepgram transcription failed for session %s", session_id)
        raise
    transcription_ms = int((time.perf_counter() - t0) * 1000)

    # Empty transcript → return early (silence, background noise)
    if not transcription.transcript.strip():
        return VoiceClipResult(
            transcript="",
            confidence=transcription.confidence,
            transcription_ms=transcription_ms,
        )

    # Step 2: Load context from DB
    existing_entries = await entry_service.list_entries_by_session(db, session_id)
    context_dicts = [_entry_to_context_dict(e) for e in existing_entries]

    # Step 3: Parse
    t1 = time.perf_counter()
    try:
        parser_result = await parse_transcript(
            transcription.transcript,
            session_context=context_dicts if context_dicts else None,
        )
    except Exception:
        logger.exception("Claude parser failed for session %s", session_id)
        raise
    parsing_ms = int((time.perf_counter() - t1) * 1000)

    # Step 4: Validate
    t2 = time.perf_counter()
    validation_result = validate_parser_result(
        parser_result,
        default_weight_unit=default_weight_unit,
        context_entry_count=len(existing_entries),
    )
    validation_ms = int((time.perf_counter() - t2) * 1000)
    all_warnings.extend(validation_result.warnings)

    # Step 5: Persist
    t3 = time.perf_counter()
    next_seq = await entry_service.get_next_sequence_order(db, session_id)
    created: list[SessionEntry] = []
    modified: list[SessionEntry] = []
    clarifications: list[ClarificationItem] = []

    # Persist exercise cards
    for card in validation_result.exercise_cards:
        entry = await _persist_exercise_card(
            db, card, session_id, client_id, next_seq,
        )
        created.append(entry)
        next_seq += 1

    # Persist observation cards (non-yellow) / collect clarifications (yellow)
    for card in validation_result.observation_cards:
        if card.flag_color == "yellow":
            clarifications.append(ClarificationItem(
                observation_text=card.observation_text,
                flag_reason=card.flag_reason,
            ))
        else:
            entry = await _persist_observation_card(
                db, card, session_id, client_id, next_seq,
            )
            created.append(entry)
            next_seq += 1

    # Apply modifications to existing entries
    for mod in validation_result.modifications:
        # Skip out-of-range targets (validation layer already warned)
        if mod.target_entry_id < 1 or mod.target_entry_id > len(existing_entries):
            continue

        target_entry = existing_entries[mod.target_entry_id - 1]

        if target_entry.entry_type != EntryTypeEnum.exercise_card:
            all_warnings.append(ValidationWarning(
                field="target_entry_id",
                code="target_not_exercise",
                message=(
                    f"Modification target [{mod.target_entry_id}] is an "
                    f"{target_entry.entry_type.value}, not an exercise_card. Skipped."
                ),
            ))
            continue

        # Warn if updates target sets but entry has none
        if mod.updates and not target_entry.sets:
            all_warnings.append(ValidationWarning(
                field="target_entry_id",
                code="target_has_no_sets",
                message=(
                    f"Modification target [{mod.target_entry_id}] has no sets "
                    f"to update. Set-level updates skipped."
                ),
            ))

        update_kwargs = _build_modification_kwargs(target_entry, mod)
        if update_kwargs:
            updated = await entry_service.update_entry(db, target_entry, **update_kwargs)
            modified.append(updated)

    persistence_ms = int((time.perf_counter() - t3) * 1000)

    return VoiceClipResult(
        entries_created=tuple(created),
        entries_modified=tuple(modified),
        clarifications=tuple(clarifications),
        warnings=tuple(all_warnings),
        transcript=transcription.transcript,
        confidence=transcription.confidence,
        transcription_ms=transcription_ms,
        parsing_ms=parsing_ms,
        validation_ms=validation_ms,
        persistence_ms=persistence_ms,
    )
