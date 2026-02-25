"""Deepgram speech-to-text service.

Handles audio transcription via Deepgram Nova-3 with gym-specific
keyterm prompting for improved exercise name recognition.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from deepgram import DeepgramClient, PrerecordedOptions

from app.config import settings

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXERCISE_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "exercise_db.json"

# Gym jargon that Deepgram wouldn't recognize without prompting.
# These are terms trainers use that aren't exercise names.
GYM_TERMS: list[str] = [
    "RPE",
    "RIR",
    "reps in reserve",
    "AMRAP",
    "EMOM",
    "superset",
    "drop set",
    "rest-pause",
    "tempo",
    "eccentric",
    "concentric",
    "isometric",
    "hypertrophy",
    "deload",
    "one rep max",
    "PR",
    "PB",
    "spotter",
    "racking",
    "re-rack",
    "unrack",
]

# Common single words Deepgram already handles well — no keyterm needed.
_SKIP_TERMS: set[str] = {
    "squat",
    "bench",
    "press",
    "curl",
    "row",
    "pull",
    "push",
    "lunge",
    "plank",
    "crunch",
    "dip",
    "shrug",
    "fly",
    "raise",
    "twist",
    "slam",
    "walk",
    "jump",
}

KEYTERM_LIMIT = 100


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WordInfo:
    """A single word from the transcript with timing data."""

    word: str
    start: float
    end: float
    confidence: float


@dataclass(frozen=True)
class TranscriptionResult:
    """Result from Deepgram transcription."""

    transcript: str
    confidence: float
    duration_seconds: float
    words: tuple[WordInfo, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Exercise database loading
# ---------------------------------------------------------------------------

def load_exercise_db(path: Path = EXERCISE_DB_PATH) -> list[dict]:
    """Load the exercise database from JSON.

    Args:
        path: Path to exercise_db.json. Defaults to the bundled file.

    Returns:
        List of exercise dicts with canonical_name, aliases, etc.

    Raises:
        FileNotFoundError: If the JSON file doesn't exist.
        json.JSONDecodeError: If the JSON is malformed.
    """
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Keyterm list builder
# ---------------------------------------------------------------------------

def _is_multi_word(term: str) -> bool:
    """Check if a term has multiple words (Deepgram needs help with these)."""
    return " " in term or "-" in term


def _is_abbreviation(term: str) -> bool:
    """Check if a term is an abbreviation (all caps, short)."""
    return term.isupper() and len(term) <= 6


def build_keyterm_list(exercises: list[dict] | None = None) -> list[str]:
    """Build a prioritized list of keyterms for Deepgram prompting.

    Selects terms that Deepgram would likely misrecognize: multi-word
    exercise names, abbreviations, and gym jargon. Skips common single
    English words that Deepgram handles fine on its own.

    Args:
        exercises: List of exercise dicts. If None, loads from the
            default exercise_db.json.

    Returns:
        Deduplicated list of keyterms, capped at 100.
    """
    if exercises is None:
        exercises = load_exercise_db()

    # Priority 1: gym jargon (RPE, AMRAP, etc.) — always included
    # Priority 2: abbreviations from aliases (RDL, OHP, GHR, etc.)
    # Priority 3: multi-word exercise names and aliases
    abbreviations: list[str] = []
    multi_word: list[str] = []

    for exercise in exercises:
        canonical = exercise["canonical_name"]

        # Multi-word canonical names always need help
        if _is_multi_word(canonical):
            multi_word.append(canonical)

        # Check aliases for abbreviations and multi-word terms
        for alias in exercise.get("aliases", []):
            if _is_abbreviation(alias):
                abbreviations.append(alias)
            elif _is_multi_word(alias) and alias.lower() not in _SKIP_TERMS:
                multi_word.append(alias)

    # Build in priority order: gym terms first, then abbreviations, then multi-word
    candidates = list(GYM_TERMS) + abbreviations + multi_word

    # Deduplicate while preserving priority order
    seen: set[str] = set()
    unique: list[str] = []
    for term in candidates:
        lower = term.lower()
        if lower not in seen and lower not in _SKIP_TERMS:
            seen.add(lower)
            unique.append(term)

    return unique[:KEYTERM_LIMIT]


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------

async def transcribe_audio(
    audio_data: bytes,
    *,
    mime_type: str = "audio/wav",
    keyterms: list[str] | None = None,
) -> TranscriptionResult:
    """Transcribe audio using Deepgram Nova-3.

    Args:
        audio_data: Raw audio bytes.
        mime_type: MIME type of the audio (e.g. "audio/wav", "audio/webm").
        keyterms: Optional keyterm list for vocabulary prompting.
            If None, builds the default list from the exercise database.

    Returns:
        TranscriptionResult with transcript, confidence, duration, and words.

    Raises:
        ValueError: If audio_data is empty.
        deepgram.DeepgramError: If the Deepgram API call fails.
    """
    if not audio_data:
        raise ValueError("audio_data must not be empty")

    if keyterms is None:
        keyterms = build_keyterm_list()

    client = DeepgramClient(api_key=settings.deepgram_api_key)

    options = PrerecordedOptions(
        model="nova-3",
        language="en",
        punctuate=True,
        smart_format=True,
        keyterm=keyterms,
    )

    response = await client.listen.asyncrest.transcribe_file(
        {"buffer": audio_data, "mimetype": mime_type},
        options=options,
    )

    # Extract results from first channel, first alternative.
    # Deepgram may return empty channels/alternatives on silence or errors.
    channels = response.results.channels
    if not channels or not channels[0].alternatives:
        return TranscriptionResult(
            transcript="",
            confidence=0.0,
            duration_seconds=response.metadata.duration,
        )

    channel = channels[0]
    alternative = channel.alternatives[0]

    words = tuple(
        WordInfo(
            word=w.word,
            start=w.start,
            end=w.end,
            confidence=w.confidence,
        )
        for w in alternative.words
    )

    return TranscriptionResult(
        transcript=alternative.transcript,
        confidence=alternative.confidence,
        duration_seconds=response.metadata.duration,
        words=words,
    )
