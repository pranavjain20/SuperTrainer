"""Validation layer for parsed transcript data.

Sits between the parser and the voice endpoint. Takes raw parser output
(exercise names as spoken, weights in original units, unstructured
observations) and normalizes it: fuzzy-matches exercises to the canonical
DB, converts weights to kg, validates set data, and extracts structured
pain mentions from observation text.

Design principles:
- Pure functions, no DB access. Exercise DB loaded from JSON.
- Warnings, not exceptions. Partial results are useful.
- No modification of parser dataclasses — consumes read-only, produces
  its own output types.
- Thresholds (auto-apply vs suggest vs unmatched) live in the voice
  endpoint, not here. We return confidence scores and let the caller
  decide.
"""

import re
from dataclasses import dataclass

from rapidfuzz import fuzz, process

from app.services.parser import (
    ParsedExerciseCard,
    ParsedModification,
    ParsedObservationCard,
    ParserResult,
)
from app.services.transcription import load_exercise_db

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LBS_TO_KG = 0.453592


def convert_rir_to_rpe(rir: float) -> float:
    """Convert Reps In Reserve to Rate of Perceived Exertion.

    Formula: RPE = 10 - RIR, clamped to 1.0-10.0.
    Handles half-points naturally (RIR 1.5 → RPE 8.5).
    """
    rpe = 10.0 - rir
    return max(1.0, min(10.0, rpe))

# ---------------------------------------------------------------------------
# Pain extraction constants
# ---------------------------------------------------------------------------

# Maps colloquial body part terms to standardized names.
# Longer keys checked first to avoid "back" matching before "lower back".
BODY_PART_MAP: dict[str, str] = {
    "lower back": "lower back",
    "low back": "lower back",
    "upper back": "upper back",
    "mid back": "mid back",
    "middle back": "mid back",
    "left knee": "left knee",
    "right knee": "right knee",
    "left shoulder": "left shoulder",
    "right shoulder": "right shoulder",
    "left hip": "left hip",
    "right hip": "right hip",
    "left elbow": "left elbow",
    "right elbow": "right elbow",
    "left wrist": "left wrist",
    "right wrist": "right wrist",
    "left ankle": "left ankle",
    "right ankle": "right ankle",
    "knees": "knee",
    "knee": "knee",
    "shoulders": "shoulder",
    "shoulder": "shoulder",
    "hips": "hip",
    "hip": "hip",
    "elbows": "elbow",
    "elbow": "elbow",
    "wrists": "wrist",
    "wrist": "wrist",
    "ankles": "ankle",
    "ankle": "ankle",
    "neck": "neck",
    "back": "back",
    "quads": "quadriceps",
    "quadriceps": "quadriceps",
    "quad": "quadriceps",
    "hamstrings": "hamstring",
    "hamstring": "hamstring",
    "hammies": "hamstring",
    "calves": "calf",
    "calf": "calf",
    "glutes": "glute",
    "glute": "glute",
    "groin": "groin",
    "shin": "shin",
    "shins": "shin",
    "achilles": "achilles",
    "rotator cuff": "rotator cuff",
    "bicep": "bicep",
    "biceps": "bicep",
    "tricep": "tricep",
    "triceps": "tricep",
    "forearm": "forearm",
    "forearms": "forearm",
    "chest": "chest",
    "pec": "chest",
    "pecs": "chest",
    "abs": "abdominals",
    "core": "abdominals",
    "foot": "foot",
    "feet": "foot",
    # Spine regions
    "thoracic spine": "thoracic spine",
    "cervical spine": "cervical spine",
    "lumbar spine": "lumbar spine",
    "t-spine": "thoracic spine",
    "c-spine": "cervical spine",
    "thoracic": "thoracic spine",
    "cervical": "cervical spine",
    "lumbar": "lumbar spine",
    # Muscles
    "trapezius": "trapezius",
    "traps": "trapezius",
    "trap": "trapezius",
    "latissimus": "latissimus",
    "lats": "latissimus",
    "lat": "latissimus",
    "adductors": "adductor",
    "adductor": "adductor",
    "obliques": "oblique",
    "oblique": "oblique",
    "hip flexors": "hip flexor",
    "hip flexor": "hip flexor",
    # Joints / bands
    "it band": "IT band",
    "si joint": "SI joint",
    "plantar fascia": "plantar fascia",
    # Digits
    "big toe": "big toe",
    "toes": "toe",
    "toe": "toe",
    "fingers": "finger",
    "finger": "finger",
    "thumb": "thumb",
}

# Sorted longest-first so "lower back" matches before "back"
_BODY_PART_KEYS_SORTED: list[str] = sorted(BODY_PART_MAP.keys(), key=len, reverse=True)

PAIN_KEYWORDS: set[str] = {
    "pain",
    "painful",
    "hurt",
    "hurts",
    "hurting",
    "sore",
    "soreness",
    "tight",
    "tightness",
    "sharp",
    "ache",
    "aching",
    "achy",
    "throb",
    "throbbing",
    "twinge",
    "pinch",
    "pinching",
    "pull",
    "pulled",
    "strain",
    "strained",
    "spasm",
    "cramp",
    "cramping",
    "stiff",
    "stiffness",
    "tender",
    "tenderness",
    "inflamed",
    "inflammation",
    "swollen",
    "swelling",
    "discomfort",
    "uncomfortable",
    "irritated",
    "irritation",
    "burning",
    "numb",
    "numbness",
    "tingling",
    # Sounds
    "pop",
    "popped",
    "popping",
    "crack",
    "cracked",
    "cracking",
    "click",
    "clicked",
    "clicking",
    "snap",
    "snapped",
    "snapping",
    "tear",
    "tore",
    "torn",
    # States
    "gave out",
    "buckled",
    "locked up",
    "seized",
    "seized up",
    "went numb",
    # Colloquial
    "tweaked",
    "aggravated",
    "flared up",
    "acting up",
    "messed up",
    # Sensations
    "shooting",
    "radiating",
    "stabbing",
    "pulsing",
}

# Pre-compiled word-boundary regex for pain keywords.
# Longest-first so multi-word phrases like "gave out" match before "gave".
_PAIN_KEYWORD_PATTERN = re.compile(
    r"\b(?:" + "|".join(
        re.escape(kw) for kw in sorted(PAIN_KEYWORDS, key=len, reverse=True)
    ) + r")\b",
    re.IGNORECASE,
)

# Maps severity modifiers to a 1-10 estimate.
SEVERITY_MODIFIERS: dict[str, int] = {
    "a little": 2,
    "a bit": 2,
    "slight": 2,
    "slightly": 2,
    "minor": 3,
    "mild": 3,
    "mildly": 3,
    "some": 4,
    "moderate": 5,
    "moderately": 5,
    "quite": 6,
    "pretty": 6,
    "really": 7,
    "very": 7,
    "sharp": 7,
    "bad": 7,
    "significant": 7,
    "severe": 8,
    "severely": 8,
    "intense": 8,
    "extreme": 9,
    "extremely": 9,
    "terrible": 9,
    "excruciating": 10,
    # Nerve / tissue damage indicators
    "shooting": 8,
    "radiating": 8,
    "stabbing": 8,
    # Low-grade
    "dull": 3,
    "nagging": 4,
    # Persistent
    "constant": 5,
    "persistent": 5,
    # Manageable
    "bearable": 3,
    "manageable": 3,
}

# Sorted longest-first for matching
_SEVERITY_KEYS_SORTED: list[str] = sorted(SEVERITY_MODIFIERS.keys(), key=len, reverse=True)

DEFAULT_SEVERITY = 5

# ---------------------------------------------------------------------------
# Negation phrases — if any appear in a clause, skip the pain mention
# ---------------------------------------------------------------------------

_NEGATION_PHRASES: tuple[str, ...] = (
    "pain-free",
    "pain free",
    "doesn't hurt",
    "didn't hurt",
    "don't feel",
    "not hurt",
    "not pain",
    "no longer",
    "resolved",
    "went away",
    "better now",
    "improved",
    "feels better",
    "feeling better",
)

# Matches "no" followed by 0-3 words followed by a pain-related term.
# Handles "no pain", "no knee pain", "no left shoulder soreness", etc.
_NEGATION_NO_PATTERN = re.compile(
    r"\bno\b\s+(?:\w+\s+){0,3}"
    r"(?:pain|soreness|tightness|discomfort|hurt|hurts|ache|aching)\b",
    re.IGNORECASE,
)


def _is_negated(sentence_lower: str) -> bool:
    """Check if a clause contains a negation phrase or pattern."""
    if any(phrase in sentence_lower for phrase in _NEGATION_PHRASES):
        return True
    return _NEGATION_NO_PATTERN.search(sentence_lower) is not None


# ---------------------------------------------------------------------------
# Output dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValidationWarning:
    """A non-fatal issue found during validation."""

    field: str
    code: str
    message: str


@dataclass(frozen=True)
class ExerciseMatch:
    """Result of fuzzy-matching an exercise name to the canonical DB."""

    canonical_name: str
    confidence: int  # 0-100
    matched_alias: str  # the alias or canonical name that matched


@dataclass(frozen=True)
class ValidatedSet:
    """A single set with normalized weight (always kg internally)."""

    reps: int
    weight_kg: float | None = None
    weight_original: float | None = None
    weight_unit_original: str | None = None
    rpe: float | None = None
    duration_seconds: int | None = None
    rir: float | None = None
    equipment_note: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class PainMention:
    """Structured pain data extracted from observation text."""

    body_part: str
    severity_estimate: int  # 1-10
    description: str
    raw_text: str


@dataclass(frozen=True)
class ValidatedExerciseCard:
    """An exercise card with normalized data, ready for DB insertion."""

    exercise_name: str  # original, as spoken
    exercise_match: ExerciseMatch | None
    sets: tuple[ValidatedSet, ...] | None
    total_volume_kg: float | None
    form_notes: tuple[str, ...]
    cues_given: tuple[str, ...]
    warnings: tuple[ValidationWarning, ...]


@dataclass(frozen=True)
class ValidatedObservationCard:
    """An observation card with extracted pain mentions."""

    observation_text: str
    flag_color: str | None
    flag_reason: str | None
    pain_mentions: tuple[PainMention, ...]
    warnings: tuple[ValidationWarning, ...]
    target_entry_id: int | None = None
    attached_to_set: int | None = None


@dataclass(frozen=True)
class ValidatedModification:
    """A validated modification to an existing exercise card."""

    target_entry_id: int
    action: str  # "add" or "correct"
    target_sets: tuple[int, ...] | None
    updates: dict | None
    add_sets: tuple[ValidatedSet, ...] | None
    form_notes: tuple[str, ...]
    cues_given: tuple[str, ...]
    warnings: tuple[ValidationWarning, ...]


@dataclass(frozen=True)
class ValidationResult:
    """Complete validation output — exercise cards, observation cards,
    modifications, and any warnings."""

    exercise_cards: tuple[ValidatedExerciseCard, ...]
    observation_cards: tuple[ValidatedObservationCard, ...]
    modifications: tuple[ValidatedModification, ...]
    tool_call_order: tuple[str, ...]
    warnings: tuple[ValidationWarning, ...]


# ---------------------------------------------------------------------------
# Exercise matching
# ---------------------------------------------------------------------------


def build_exercise_lookup(exercises: list[dict]) -> dict[str, str]:
    """Build a flat {alias_lower: canonical_name} mapping from the exercise DB.

    Includes the canonical name itself (lowercased) and all aliases.
    Used for exact-match shortcut and as the corpus for fuzzy matching.

    Args:
        exercises: List of exercise dicts from exercise_db.json.

    Returns:
        Dict mapping lowercased name/alias to canonical_name.
    """
    lookup: dict[str, str] = {}
    for exercise in exercises:
        canonical = exercise["canonical_name"]
        lookup[canonical.lower()] = canonical
        for alias in exercise.get("aliases", []):
            lookup[alias.lower()] = canonical
    return lookup


def match_exercise_name(
    name: str,
    lookup: dict[str, str],
    score_cutoff: int = 40,
) -> ExerciseMatch | None:
    """Fuzzy-match an exercise name against the canonical DB.

    First tries exact match (case-insensitive) for O(1) lookup.
    Falls back to rapidfuzz WRatio for fuzzy matching.

    Args:
        name: Exercise name as spoken by the trainer.
        lookup: Dict from build_exercise_lookup().
        score_cutoff: Minimum fuzzy score to accept (0-100). Default 40.

    Returns:
        ExerciseMatch with canonical name and confidence, or None if no
        match above the cutoff.
    """
    if not name or not name.strip():
        return None

    name_lower = name.strip().lower()

    # Exact match — confidence 100
    if name_lower in lookup:
        return ExerciseMatch(
            canonical_name=lookup[name_lower],
            confidence=100,
            matched_alias=name_lower,
        )

    # Fuzzy match against all keys
    result = process.extractOne(
        name_lower,
        lookup.keys(),
        scorer=fuzz.WRatio,
        score_cutoff=score_cutoff,
    )

    if result is None:
        return None

    matched_alias, score, _ = result
    return ExerciseMatch(
        canonical_name=lookup[matched_alias],
        confidence=int(round(score)),
        matched_alias=matched_alias,
    )


# ---------------------------------------------------------------------------
# Weight normalization
# ---------------------------------------------------------------------------


def normalize_weight(
    weight: float | None,
    weight_unit: str | None,
    default_unit: str = "kg",
) -> tuple[float | None, str | None, list[ValidationWarning]]:
    """Convert weight to kg for internal storage.

    Args:
        weight: Raw weight value (may be None).
        weight_unit: "kg", "lbs", or None (use default_unit).
        default_unit: Unit to assume when weight_unit is None.

    Returns:
        Tuple of (weight_in_kg, original_unit, warnings).
        weight_in_kg and original_unit are both None if weight is None.
    """
    if weight is None:
        return None, None, []

    unit = weight_unit or default_unit

    if unit == "lbs":
        return round(weight * LBS_TO_KG, 1), "lbs", []

    if unit != "kg":
        return round(weight, 1), "kg", [ValidationWarning(
            field="weight_unit",
            code="unknown_weight_unit",
            message=f"Unknown weight unit '{unit}'. Defaulting to kg.",
        )]

    return round(weight, 1), "kg", []


# ---------------------------------------------------------------------------
# Set validation
# ---------------------------------------------------------------------------


def validate_set(
    parsed_set: dict,
    default_weight_unit: str = "kg",
) -> tuple[ValidatedSet, list[ValidationWarning]]:
    """Validate and normalize a single parsed set.

    Checks that values are within sane ranges and converts weight to kg.

    Args:
        parsed_set: Dict with reps, weight, weight_unit, rpe, duration_seconds.
            Can come from ParsedSet.__dict__ or raw dict.
        default_weight_unit: Unit to assume when weight_unit is missing.

    Returns:
        Tuple of (ValidatedSet, list of warnings).
    """
    warnings: list[ValidationWarning] = []

    # Reps validation
    reps = parsed_set.get("reps", 0)
    if not isinstance(reps, int) or reps <= 0:
        warnings.append(ValidationWarning(
            field="reps",
            code="invalid_reps",
            message=f"Invalid reps value: {reps}. Must be a positive integer.",
        ))
        reps = max(1, reps) if isinstance(reps, int) else 1

    if isinstance(reps, int) and reps > 100:
        warnings.append(ValidationWarning(
            field="reps",
            code="suspicious_reps",
            message=f"Reps value {reps} is unusually high. Confirm with trainer.",
        ))

    # Weight normalization
    raw_weight = parsed_set.get("weight")
    raw_unit = parsed_set.get("weight_unit")

    if raw_weight is not None and raw_weight < 0:
        warnings.append(ValidationWarning(
            field="weight",
            code="negative_weight",
            message=f"Negative weight: {raw_weight}. Using absolute value.",
        ))
        raw_weight = abs(raw_weight)

    weight_kg, original_unit, weight_warnings = normalize_weight(
        raw_weight, raw_unit, default_weight_unit,
    )
    warnings.extend(weight_warnings)

    if weight_kg is not None and weight_kg > 500:
        warnings.append(ValidationWarning(
            field="weight",
            code="suspicious_weight",
            message=f"Weight {weight_kg}kg is unusually high. Confirm with trainer.",
        ))

    # RIR validation (0-10 scale)
    rir = parsed_set.get("rir")
    if rir is not None:
        # Coerce string to number (Claude occasionally sends "2" instead of 2)
        if isinstance(rir, str):
            try:
                rir = float(rir)
            except ValueError:
                rir = None
        if rir is not None and not isinstance(rir, (int, float)):
            rir = None
        elif rir < 0:
            warnings.append(ValidationWarning(
                field="rir",
                code="invalid_rir",
                message=f"RIR {rir} below zero. Clamped to 0.",
            ))
            rir = 0.0
        elif rir > 10:
            warnings.append(ValidationWarning(
                field="rir",
                code="invalid_rir",
                message=f"RIR {rir} above 10. Clamped to 10.",
            ))
            rir = 10.0

    # RPE validation (1-10 scale)
    rpe = parsed_set.get("rpe")
    if rpe is not None:
        # Coerce string to number (same as RIR above)
        if isinstance(rpe, str):
            try:
                rpe = float(rpe)
            except ValueError:
                rpe = None
        if rpe is not None and (not isinstance(rpe, (int, float)) or rpe < 1 or rpe > 10):
            warnings.append(ValidationWarning(
                field="rpe",
                code="invalid_rpe",
                message=f"RPE {rpe} out of range (1-10).",
            ))
            rpe = max(1, min(10, rpe)) if isinstance(rpe, (int, float)) else None

    # RIR→RPE conversion: if RIR present and no RPE, derive RPE
    if rir is not None and rpe is None:
        rpe = convert_rir_to_rpe(rir)

    # RIR+RPE conflict: if both present and disagree, trust RIR
    if rir is not None and rpe is not None and parsed_set.get("rpe") is not None:
        expected_rpe = convert_rir_to_rpe(rir)
        if abs(expected_rpe - rpe) > 0.5:
            warnings.append(ValidationWarning(
                field="rpe",
                code="rir_rpe_conflict",
                message=(
                    f"RIR {rir} implies RPE {expected_rpe}, but RPE {rpe} "
                    f"was also provided. Using RIR-derived RPE."
                ),
            ))
            rpe = expected_rpe

    # Equipment note and per-set notes: passthrough, no validation needed
    equipment_note = parsed_set.get("equipment_note")
    notes = parsed_set.get("notes")

    # Duration validation
    duration = parsed_set.get("duration_seconds")
    if duration is not None:
        if not isinstance(duration, int) or duration <= 0:
            warnings.append(ValidationWarning(
                field="duration_seconds",
                code="invalid_duration",
                message=f"Invalid duration: {duration}. Must be positive.",
            ))
            duration = max(1, duration) if isinstance(duration, int) else None

    return ValidatedSet(
        reps=reps,
        weight_kg=weight_kg,
        weight_original=raw_weight,
        weight_unit_original=original_unit,
        rpe=rpe,
        duration_seconds=duration,
        rir=rir,
        equipment_note=equipment_note,
        notes=notes,
    ), warnings


def calculate_total_volume(sets: tuple[ValidatedSet, ...] | None) -> float | None:
    """Calculate total volume (sum of reps * weight_kg) across sets.

    Returns None if no sets have weight data (bodyweight exercises, etc).
    """
    if not sets:
        return None

    total = 0.0
    has_weight = False
    for s in sets:
        if s.weight_kg is not None:
            total += s.reps * s.weight_kg
            has_weight = True

    return round(total, 1) if has_weight else None


# ---------------------------------------------------------------------------
# Pain extraction
# ---------------------------------------------------------------------------


def _has_pain_keyword(text_lower: str) -> bool:
    """Quick check: does the text contain any pain keyword (word-boundary safe)?"""
    return _PAIN_KEYWORD_PATTERN.search(text_lower) is not None


def _find_body_parts(text_lower: str) -> list[tuple[str, str]]:
    """Find all body part mentions in text.

    Returns list of (standardized_name, matched_term) tuples.
    Checks longest terms first to avoid partial matches.
    """
    found: list[tuple[str, str]] = []
    already_matched_spans: list[tuple[int, int]] = []

    for term in _BODY_PART_KEYS_SORTED:
        start = 0
        while True:
            idx = text_lower.find(term, start)
            if idx == -1:
                break

            end = idx + len(term)

            # Check word boundaries to avoid matching "shin" inside "shining"
            before_ok = idx == 0 or not text_lower[idx - 1].isalpha()
            after_ok = end >= len(text_lower) or not text_lower[end].isalpha()

            if before_ok and after_ok:
                # Check this span doesn't overlap with an already-matched span
                overlaps = any(
                    not (end <= ms or idx >= me)
                    for ms, me in already_matched_spans
                )
                if not overlaps:
                    found.append((BODY_PART_MAP[term], term))
                    already_matched_spans.append((idx, end))

            start = end

    return found


def _find_severity(text_lower: str) -> int:
    """Find the highest severity modifier in text, or return default."""
    best = DEFAULT_SEVERITY
    found_any = False

    for modifier in _SEVERITY_KEYS_SORTED:
        if modifier in text_lower:
            score = SEVERITY_MODIFIERS[modifier]
            if not found_any or score > best:
                best = score
                found_any = True

    return best if found_any else DEFAULT_SEVERITY


def extract_pain_mentions(observation_text: str) -> list[PainMention]:
    """Extract structured pain mentions from observation text.

    Uses keyword matching + body part mapping. Intentionally simple —
    not NLP. Designed to catch explicit pain reports from trainers.

    Strategy:
    1. Quick reject if no pain keyword in text
    2. Split into sentences
    3. For each sentence: find body parts + pain keywords
    4. Both present → look for severity → build PainMention
    5. Deduplicate: same body part → keep highest severity

    Args:
        observation_text: The observation text to scan.

    Returns:
        List of PainMention objects, deduplicated by body part.
    """
    if not observation_text or not observation_text.strip():
        return []

    text_lower = observation_text.lower()

    # Quick reject
    if not _has_pain_keyword(text_lower):
        return []

    # Split into clauses (period, semicolon, comma, exclamation, or newline)
    sentences = re.split(r'[.;!,\n]+', observation_text)

    mentions_by_part: dict[str, PainMention] = {}

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        sentence_lower = sentence.lower()

        # Check for pain keywords in this clause (word-boundary safe)
        if not _PAIN_KEYWORD_PATTERN.search(sentence_lower):
            continue

        # Skip negated clauses ("no pain", "doesn't hurt", etc.)
        if _is_negated(sentence_lower):
            continue

        # Find body parts in this sentence
        body_parts = _find_body_parts(sentence_lower)
        if not body_parts:
            continue

        # Find severity
        severity = _find_severity(sentence_lower)

        for standardized, matched_term in body_parts:
            mention = PainMention(
                body_part=standardized,
                severity_estimate=severity,
                description=sentence,
                raw_text=sentence,
            )

            # Dedup: keep highest severity per body part
            if standardized not in mentions_by_part:
                mentions_by_part[standardized] = mention
            elif severity > mentions_by_part[standardized].severity_estimate:
                mentions_by_part[standardized] = mention

    return list(mentions_by_part.values())


# ---------------------------------------------------------------------------
# Card validators
# ---------------------------------------------------------------------------


def validate_exercise_card(
    card: ParsedExerciseCard,
    lookup: dict[str, str],
    default_weight_unit: str = "kg",
) -> ValidatedExerciseCard:
    """Validate and normalize a parsed exercise card.

    Fuzzy-matches the exercise name, validates each set, and calculates
    total volume.

    Args:
        card: Parsed exercise card from the parser.
        lookup: Exercise name lookup from build_exercise_lookup().
        default_weight_unit: Default weight unit for sets missing units.

    Returns:
        ValidatedExerciseCard with normalized data.
    """
    warnings: list[ValidationWarning] = []

    # Exercise name matching
    match = match_exercise_name(card.exercise_name, lookup)
    if match is None:
        warnings.append(ValidationWarning(
            field="exercise_name",
            code="no_match",
            message=f"No canonical match for '{card.exercise_name}'.",
        ))

    # Validate sets
    validated_sets: list[ValidatedSet] | None = None
    if card.sets is not None:
        validated_sets = []
        for parsed_set in card.sets:
            # Convert ParsedSet to dict for validate_set
            set_dict = {
                "reps": parsed_set.reps,
                "weight": parsed_set.weight,
                "weight_unit": parsed_set.weight_unit,
                "rpe": parsed_set.rpe,
                "duration_seconds": parsed_set.duration_seconds,
                "rir": parsed_set.rir,
                "equipment_note": parsed_set.equipment_note,
                "notes": parsed_set.notes,
            }
            validated, set_warnings = validate_set(set_dict, default_weight_unit)
            validated_sets.append(validated)
            warnings.extend(set_warnings)

    sets_tuple = tuple(validated_sets) if validated_sets is not None else None
    total_volume = calculate_total_volume(sets_tuple)

    return ValidatedExerciseCard(
        exercise_name=card.exercise_name,
        exercise_match=match,
        sets=sets_tuple,
        total_volume_kg=total_volume,
        form_notes=card.form_notes,
        cues_given=card.cues_given,
        warnings=tuple(warnings),
    )


def validate_observation_card(
    card: ParsedObservationCard,
    context_entry_count: int = 0,
) -> ValidatedObservationCard:
    """Validate an observation card and extract pain mentions.

    Validates target_entry_id / attached_to_set attachment fields:
    - target_entry_id must be in range (1 to context_entry_count)
    - attached_to_set without target_entry_id is orphaned → cleared
    - attached_to_set < 1 is invalid → cleared
    - target_entry_id without context → cleared

    Args:
        card: Parsed observation card from the parser.
        context_entry_count: Number of entries in the current session context.

    Returns:
        ValidatedObservationCard with pain mentions extracted.
    """
    warnings: list[ValidationWarning] = []

    pain_mentions = extract_pain_mentions(card.observation_text)

    # Validate attachment fields
    target_entry_id = card.target_entry_id
    attached_to_set = card.attached_to_set

    if target_entry_id is not None:
        if context_entry_count == 0:
            # No context — can't target anything
            warnings.append(ValidationWarning(
                field="target_entry_id",
                code="no_context",
                message=(
                    f"Observation targets entry [{target_entry_id}] but no "
                    f"session context is available. Cleared."
                ),
            ))
            target_entry_id = None
            attached_to_set = None
        elif target_entry_id < 1 or target_entry_id > context_entry_count:
            warnings.append(ValidationWarning(
                field="target_entry_id",
                code="invalid_target",
                message=(
                    f"Observation targets entry [{target_entry_id}] but session "
                    f"has {context_entry_count} entries. Cleared."
                ),
            ))
            target_entry_id = None
            attached_to_set = None

    if attached_to_set is not None:
        if target_entry_id is None:
            # Orphan: set number without a target exercise
            warnings.append(ValidationWarning(
                field="attached_to_set",
                code="orphan_set",
                message=(
                    f"attached_to_set={attached_to_set} without target_entry_id. Cleared."
                ),
            ))
            attached_to_set = None
        elif attached_to_set < 1:
            warnings.append(ValidationWarning(
                field="attached_to_set",
                code="invalid_set",
                message=(
                    f"attached_to_set={attached_to_set} is below 1. Cleared."
                ),
            ))
            attached_to_set = None

    return ValidatedObservationCard(
        observation_text=card.observation_text,
        flag_color=card.flag_color,
        flag_reason=card.flag_reason,
        pain_mentions=tuple(pain_mentions),
        warnings=tuple(warnings),
        target_entry_id=target_entry_id,
        attached_to_set=attached_to_set,
    )


def validate_modification(
    mod: ParsedModification,
    context_entry_count: int,
    default_weight_unit: str = "kg",
) -> tuple[ValidatedModification, list[ValidationWarning]]:
    """Validate a parsed modification against session context.

    Checks that the target entry exists and validates any weight updates.

    Args:
        mod: Parsed modification from the parser.
        context_entry_count: Number of entries in the current session context.
        default_weight_unit: Default weight unit for weight updates.

    Returns:
        Tuple of (ValidatedModification, list of warnings).
    """
    warnings: list[ValidationWarning] = []

    # Validate target_entry_id is within context bounds
    if mod.target_entry_id < 1 or mod.target_entry_id > context_entry_count:
        warnings.append(ValidationWarning(
            field="target_entry_id",
            code="invalid_target",
            message=(
                f"Target entry [{mod.target_entry_id}] out of range. "
                f"Session has {context_entry_count} entries."
            ),
        ))

    # Validate action
    if mod.action not in ("add", "correct"):
        warnings.append(ValidationWarning(
            field="action",
            code="invalid_action",
            message=f"Unknown action '{mod.action}'. Expected 'add' or 'correct'.",
        ))

    # Normalize weight in updates if present
    normalized_updates = None
    if mod.updates:
        normalized_updates = dict(mod.updates)
        if "weight" in normalized_updates:
            raw_weight = normalized_updates["weight"]
            raw_unit = normalized_updates.get("weight_unit")
            weight_kg, original_unit, weight_warnings = normalize_weight(
                raw_weight, raw_unit, default_weight_unit,
            )
            warnings.extend(weight_warnings)
            normalized_updates["weight_kg"] = weight_kg
            normalized_updates["weight_original"] = raw_weight
            normalized_updates["weight_unit_original"] = original_unit

        # RIR→RPE derivation: same logic as validate_set()
        rir = normalized_updates.get("rir")
        rpe = normalized_updates.get("rpe")
        if rir is not None and rpe is None:
            normalized_updates["rpe"] = convert_rir_to_rpe(rir)
        elif rir is not None and rpe is not None:
            expected_rpe = convert_rir_to_rpe(rir)
            if abs(expected_rpe - rpe) > 0.5:
                warnings.append(ValidationWarning(
                    field="rpe",
                    code="rir_rpe_conflict",
                    message=(
                        f"RIR {rir} implies RPE {expected_rpe}, but RPE {rpe} "
                        f"was also provided. Using RIR-derived RPE."
                    ),
                ))
                normalized_updates["rpe"] = expected_rpe

    # Validate add_sets
    validated_add_sets: list[ValidatedSet] | None = None
    if mod.add_sets is not None:
        validated_add_sets = []
        for parsed_set in mod.add_sets:
            set_dict = {
                "reps": parsed_set.reps,
                "weight": parsed_set.weight,
                "weight_unit": parsed_set.weight_unit,
                "rpe": parsed_set.rpe,
                "duration_seconds": parsed_set.duration_seconds,
                "rir": parsed_set.rir,
                "equipment_note": parsed_set.equipment_note,
                "notes": parsed_set.notes,
            }
            validated, set_warnings = validate_set(set_dict, default_weight_unit)
            validated_add_sets.append(validated)
            warnings.extend(set_warnings)

    return ValidatedModification(
        target_entry_id=mod.target_entry_id,
        action=mod.action,
        target_sets=mod.target_sets,
        updates=normalized_updates,
        add_sets=tuple(validated_add_sets) if validated_add_sets else None,
        form_notes=mod.form_notes,
        cues_given=mod.cues_given,
        warnings=tuple(warnings),
    ), warnings


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

# Lazy-loaded exercise lookup — built once on first use
_exercise_lookup_cache: dict[str, str] | None = None


def _get_exercise_lookup() -> dict[str, str]:
    """Get or build the exercise lookup from the JSON DB."""
    global _exercise_lookup_cache
    if _exercise_lookup_cache is None:
        exercises = load_exercise_db()
        _exercise_lookup_cache = build_exercise_lookup(exercises)
    return _exercise_lookup_cache


def validate_parser_result(
    parser_result: ParserResult,
    *,
    default_weight_unit: str = "kg",
    context_entry_count: int = 0,
    exercise_lookup: dict[str, str] | None = None,
) -> ValidationResult:
    """Validate a complete parser result — the single entry point.

    Takes the raw output from parse_transcript() and normalizes everything:
    fuzzy-matches exercise names, converts weights to kg, validates sets,
    and extracts pain mentions from observations.

    Args:
        parser_result: Output from parse_transcript().
        default_weight_unit: Default unit for sets missing weight_unit.
        context_entry_count: Number of entries in session context
            (for modification validation).
        exercise_lookup: Pre-built exercise lookup dict. If None, loads
            from the exercise DB lazily.

    Returns:
        ValidationResult with validated cards, modifications, and warnings.
    """
    if exercise_lookup is None:
        exercise_lookup = _get_exercise_lookup()

    all_warnings: list[ValidationWarning] = []

    # Validate exercise cards
    validated_exercises: list[ValidatedExerciseCard] = []
    for card in parser_result.exercise_cards:
        validated = validate_exercise_card(card, exercise_lookup, default_weight_unit)
        validated_exercises.append(validated)
        all_warnings.extend(validated.warnings)

    # Validate observation cards
    validated_observations: list[ValidatedObservationCard] = []
    for card in parser_result.observation_cards:
        validated = validate_observation_card(card, context_entry_count)
        validated_observations.append(validated)
        all_warnings.extend(validated.warnings)

    # Validate modifications
    validated_modifications: list[ValidatedModification] = []
    for mod in parser_result.modifications:
        validated, mod_warnings = validate_modification(
            mod, context_entry_count, default_weight_unit,
        )
        validated_modifications.append(validated)
        all_warnings.extend(mod_warnings)

    return ValidationResult(
        exercise_cards=tuple(validated_exercises),
        observation_cards=tuple(validated_observations),
        modifications=tuple(validated_modifications),
        tool_call_order=parser_result.tool_call_order,
        warnings=tuple(all_warnings),
    )
