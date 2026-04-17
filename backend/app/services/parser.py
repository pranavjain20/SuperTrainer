"""Claude transcript parser service.

Takes raw trainer speech (transcribed by Deepgram) and uses Claude's
tool_use to extract structured exercise cards and observation cards.
Supports session context for intent classification — the parser sees
what's already been logged so it can distinguish "new exercise" from
"modify existing entry."

The key insight: we define tools — record_exercise_card,
record_observation_card, and modify_exercise_card — and Claude decides
which to call based on the transcript content. The tool name IS the
classification. The input schema IS the structured output.
"""

from dataclasses import dataclass, field
from typing import Any

import anthropic

from app.config import settings

# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

# Each tool is a "form" Claude fills in. The schema defines exactly what
# fields exist, their types, and which are required. Claude's response is
# guaranteed to match this schema — the API validates it.

EXERCISE_CARD_TOOL: dict = {
    "name": "record_exercise_card",
    "description": (
        "Record a structured exercise card from the trainer's speech. "
        "Call this once per distinct exercise mentioned. If the trainer "
        "describes sets, expand them into individual set records."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "exercise_name": {
                "type": "string",
                "description": (
                    "The exercise name exactly as the trainer said it. "
                    "Do not normalize, correct spelling, or map to a "
                    "canonical name — preserve the original phrasing."
                ),
            },
            "sets": {
                "type": "array",
                "description": (
                    "Individual set records. Expand shorthand like "
                    "'3 sets of 10 at 80' into 3 separate entries. "
                    "Omit this field entirely if the trainer only named "
                    "the exercise without set details."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "reps": {
                            "type": "integer",
                            "description": "Number of repetitions in this set.",
                        },
                        "weight": {
                            "type": "number",
                            "description": (
                                "Weight used, as spoken by the trainer. "
                                "Do not convert units — record the raw number. "
                                "OMIT this field entirely if the trainer did "
                                "not mention a weight — never assume bodyweight "
                                "or any default."
                            ),
                        },
                        "weight_unit": {
                            "type": "string",
                            "enum": ["kg", "lbs"],
                            "description": (
                                "The unit the trainer used. If they said "
                                "'kilos' or 'kg', use 'kg'. If they said "
                                "'pounds' or 'lbs', use 'lbs'. If no unit "
                                "was mentioned, omit this field."
                            ),
                        },
                        "rpe": {
                            "type": "number",
                            "description": (
                                "Rate of perceived exertion (1-10) if "
                                "mentioned by the trainer."
                            ),
                        },
                        "duration_seconds": {
                            "type": "integer",
                            "description": (
                                "Duration in seconds for timed exercises "
                                "(e.g., planks, holds). Only include if "
                                "the trainer specified a time."
                            ),
                        },
                        "rir": {
                            "type": "number",
                            "description": (
                                "Reps in Reserve if mentioned. Do not "
                                "convert to RPE — record the raw RIR value."
                            ),
                        },
                        "equipment_note": {
                            "type": "string",
                            "description": (
                                "Equipment modification for this set "
                                "(e.g., 'with a red band', 'added chains')."
                            ),
                        },
                        "notes": {
                            "type": "string",
                            "description": (
                                "Any trainer commentary about this set — "
                                "form observations, technique notes, how "
                                "the set felt, pain mentions, or coaching "
                                "feedback (e.g., 'good depth', 'knees "
                                "caving in', 'felt easy', 'left shoulder "
                                "tight', 'grip slipped'). This is the "
                                "primary place for all per-set commentary."
                            ),
                        },
                    },
                    "required": ["reps"],
                },
            },
            "cues_given": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Coaching cues the trainer gave during the exercise "
                    "(e.g., 'drive through your heels', 'chest up'). "
                    "Each cue is a separate string."
                ),
            },
        },
        "required": ["exercise_name"],
    },
}

OBSERVATION_CARD_TOOL: dict = {
    "name": "record_observation_card",
    "description": (
        "Record an observation about the session or a specific exercise. "
        "Use this for injury reports, form observations, client mood/energy, "
        "or anything that doesn't fit into an exercise card. Can optionally "
        "target a specific exercise entry and set from the session context."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "observation_text": {
                "type": "string",
                "description": (
                    "The observation in clear, concise text. Preserve "
                    "the trainer's meaning but clean up speech artifacts "
                    "(ums, repeated words)."
                ),
            },
            "flag_color": {
                "type": "string",
                "enum": ["red", "yellow", "green", "clarification"],
                "description": (
                    "Severity flag — REQUIRED on every observation. "
                    "Red: pain, injury, or safety concern. "
                    "Yellow: something to watch (fatigue, minor discomfort, "
                    "form degradation). Green: positive note (PR, good "
                    "progress, milestone, neutral check-in). "
                    "Clarification: the transcript is ambiguous or unclear "
                    "and you cannot confidently extract structured data."
                ),
            },
            "flag_reason": {
                "type": "string",
                "description": (
                    "Short headline label for the flag — 2-4 words max "
                    "(e.g., 'Knee Pain', 'Volume Spike', 'New PR', "
                    "'Fatigue Warning', 'Form Breakdown'). "
                    "Required if flag_color is set."
                ),
            },
            "target_entry_id": {
                "type": "integer",
                "description": (
                    "The ID number of the exercise entry this observation "
                    "is about, from the session context (e.g., 1 for [1]). "
                    "Only set when the observation is specifically about an "
                    "exercise in the context. Omit for session-level "
                    "observations (client mood, energy, general notes)."
                ),
            },
            "attached_to_set": {
                "type": "integer",
                "description": (
                    "Which set number (1-indexed) the observation targets "
                    "within the exercise. Requires target_entry_id. For "
                    "example, 'left weaker than right on set 2' → "
                    "attached_to_set=2. Omit if the observation is about "
                    "the exercise generally, not a specific set."
                ),
            },
        },
        "required": ["observation_text", "flag_color", "flag_reason"],
    },
}

MODIFY_EXERCISE_CARD_TOOL: dict = {
    "name": "modify_exercise_card",
    "description": (
        "Modify an existing exercise card from the session context. Use this "
        "when the trainer is adding information to or correcting an exercise "
        "that was already recorded. Reference the entry by its context ID "
        "number (e.g., target_entry_id=1 for entry [1])."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "target_entry_id": {
                "type": "integer",
                "description": (
                    "The ID number of the entry to modify, from the session "
                    "context (e.g., 1 for [1], 2 for [2])."
                ),
            },
            "action": {
                "type": "string",
                "enum": ["add", "correct"],
                "description": (
                    "'add' when the trainer is providing new information "
                    "that wasn't in the original entry (e.g., adding RPE, "
                    "adding form notes). 'correct' when the trainer is "
                    "fixing a mistake in the original entry (e.g., 'no "
                    "wait, 85 not 80')."
                ),
            },
            "target_sets": {
                "type": "array",
                "items": {"type": "integer"},
                "description": (
                    "Which sets to modify, as 1-indexed set numbers. "
                    "For example, [2, 3, 4] means sets 2 through 4. "
                    "Omit this field to target ALL sets in the entry."
                ),
            },
            "updates": {
                "type": "object",
                "description": (
                    "The fields to update on the targeted sets. Only "
                    "include fields that are changing."
                ),
                "properties": {
                    "reps": {
                        "type": "integer",
                        "description": "Updated rep count.",
                    },
                    "weight": {
                        "type": "number",
                        "description": "Updated weight value.",
                    },
                    "weight_unit": {
                        "type": "string",
                        "enum": ["kg", "lbs"],
                        "description": "Updated weight unit.",
                    },
                    "rpe": {
                        "type": "number",
                        "description": "Rate of perceived exertion (1-10).",
                    },
                    "duration_seconds": {
                        "type": "integer",
                        "description": "Updated duration in seconds.",
                    },
                    "rir": {
                        "type": "number",
                        "description": (
                            "Reps in Reserve if mentioned. Do not "
                            "convert to RPE — record the raw RIR value."
                        ),
                    },
                    "equipment_note": {
                        "type": "string",
                        "description": (
                            "Equipment modification for this set "
                            "(e.g., 'with a red band', 'added chains')."
                        ),
                    },
                    "notes": {
                        "type": "string",
                        "description": (
                            "Per-set note to add — form, technique, "
                            "how it felt, pain mentions."
                        ),
                    },
                },
            },
            "add_sets": {
                "type": "array",
                "description": (
                    "New sets to APPEND to the existing entry. Use this when "
                    "the trainer records additional sets for an exercise that "
                    "was already logged (e.g., 'second set, 8 reps at 85'). "
                    "These are added after the existing sets."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "reps": {
                            "type": "integer",
                            "description": "Number of repetitions in this set.",
                        },
                        "weight": {
                            "type": "number",
                            "description": (
                                "Weight used, as spoken. OMIT entirely "
                                "if no weight was mentioned."
                            ),
                        },
                        "weight_unit": {
                            "type": "string",
                            "enum": ["kg", "lbs"],
                            "description": "The unit the trainer used.",
                        },
                        "rpe": {
                            "type": "number",
                            "description": "Rate of perceived exertion (1-10).",
                        },
                        "rir": {
                            "type": "number",
                            "description": "Reps in Reserve.",
                        },
                        "duration_seconds": {
                            "type": "integer",
                            "description": "Duration in seconds for timed exercises.",
                        },
                        "equipment_note": {
                            "type": "string",
                            "description": "Equipment modification for this set.",
                        },
                        "notes": {
                            "type": "string",
                            "description": (
                                "Any trainer commentary about this set — "
                                "form, technique, how it felt, pain."
                            ),
                        },
                    },
                    "required": ["reps"],
                },
            },
            "cues_given": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Additional coaching cues to add to the entry.",
            },
        },
        "required": ["target_entry_id", "action"],
    },
}

# All three tools — this is what we pass to the Claude API.
PARSER_TOOLS: list[dict] = [
    EXERCISE_CARD_TOOL,
    OBSERVATION_CARD_TOOL,
    MODIFY_EXERCISE_CARD_TOOL,
]

# ---------------------------------------------------------------------------
# Session context formatting
# ---------------------------------------------------------------------------

# The parser can receive prior session entries so Claude knows what's already
# been logged. This lets Claude distinguish "new exercise" from "modify the
# bench press I already recorded." Each entry gets a numbered ID ([1], [2])
# that Claude can reference when calling the modify tool.


def _format_set_summary(sets: list[dict]) -> str:
    """Format a list of set dicts into a compact summary string.

    If all sets are identical, collapses to "3×10 reps @ 80kg".
    Otherwise lists each: "Set 1: 10 reps @ 80kg, Set 2: 8 reps @ 85kg".
    """
    if not sets:
        return ""

    parts: list[str] = []
    for s in sets:
        part = f"{s['reps']} reps"
        if s.get("weight") is not None:
            unit = s.get("weight_unit") or ""
            part += f" @ {s['weight']}{unit}"
        if s.get("rpe") is not None:
            part += f" RPE {s['rpe']}"
        if s.get("rir") is not None:
            part += f" RIR {s['rir']}"
        if s.get("equipment_note"):
            part += f" [{s['equipment_note']}]"
        if s.get("duration_seconds") is not None:
            part += f" ({s['duration_seconds']}s)"
        if s.get("notes"):
            part += f" — {s['notes']}"
        parts.append(part)

    if len(set(parts)) == 1:
        return f"{len(parts)}x{parts[0]}"
    return ", ".join(f"Set {i + 1}: {p}" for i, p in enumerate(parts))


def _format_entry(index: int, entry: dict) -> str:
    """Format a single session entry into a numbered context line."""
    entry_type = entry.get("entry_type", "")

    if entry_type == "exercise_card":
        segments = [f"[{index}] Exercise: {entry['exercise_name']}"]
        if entry.get("sets"):
            segments.append(f"Sets: {_format_set_summary(entry['sets'])}")
        if entry.get("form_notes"):
            segments.append(f"Form: {', '.join(entry['form_notes'])}")
        if entry.get("cues_given"):
            segments.append(f"Cues: {', '.join(entry['cues_given'])}")
        return " | ".join(segments)

    if entry_type == "observation_card":
        text = entry.get("observation_text", "")
        line = f"[{index}] Observation: {text}"
        if entry.get("attached_to_set") is not None:
            line += f" (set {entry['attached_to_set']})"
        if entry.get("flag_color"):
            reason = entry.get("flag_reason", "")
            flag_part = f"{entry['flag_color']} flag"
            if reason:
                flag_part += f": {reason}"
            line += f" ({flag_part})"
        return line

    return f"[{index}] Unknown entry type: {entry_type}"


def format_session_context(entries: list[dict]) -> str:
    """Format prior session entries into a readable context block for Claude.

    Each entry gets a numbered ID that Claude can reference when modifying
    existing entries (e.g., "add RPE 8 to entry [1]").

    Args:
        entries: List of entry dicts as sent by the mobile client. Each dict
            should have 'entry_type' ('exercise_card' or 'observation_card')
            plus the relevant fields for that type.

    Returns:
        Formatted context string, or empty string if no entries.
    """
    if not entries:
        return ""

    lines = [f"Session context ({len(entries)} entries logged so far):"]
    for i, entry in enumerate(entries, start=1):
        lines.append(_format_entry(i, entry))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

# The tool schemas define WHAT the output looks like (the form).
# The system prompt defines HOW to fill it in (the behavioral rules).
#
# Each rule prevents a specific failure mode:
# - Rules 3, 6, 7: prevent Claude from being "too helpful" (normalizing,
#   converting, or guessing when we want raw data preserved)
# - Rules 4, 5: ensure set shorthand gets expanded into individual records
# - Rule 8: makes ambiguity safe (yellow flag > wrong guess)
# - Rule 10: handles messy real-world speech input
# - Rules 11-12: control when to modify vs create new entries
# - Rule 13: extends the "don't guess" principle to modification targeting
# - Rule 14: scopes modifications to exercise cards only
# - Rule 15: makes "correct" (overwrite) opt-in — safe by default

PARSER_SYSTEM_PROMPT: str = """\
You are a gym session transcript parser. A personal trainer has spoken \
during a training session and their speech has been transcribed. Your job \
is to extract structured data by calling the provided tools.

CRITICAL — before creating any cards, assess whether the transcript contains \
legitimate training content. If the words are clearly NOT exercise names, \
set/rep data, coaching observations, or anything training-related, you MUST \
create an observation card with flag_color="clarification" instead. Examples \
of non-training content that MUST be flagged as clarification: "donkey kong", \
"hello testing", "the weather is nice", random words, names of people/places, \
mic tests. Do NOT create exercise cards for these — they are not exercises.

Rules:
1. Call record_exercise_card once per distinct exercise mentioned.
2. Call record_observation_card ONLY for standalone observations between \
exercises — client mood, energy, session-level check-ins. Anything said \
DURING an exercise (form, technique, how a set felt, pain, coaching \
feedback) belongs as `notes` on the relevant set(s), NOT as a separate \
observation card. Use target_entry_id and attached_to_set when the \
observation is about a specific exercise or set in the context.
3. Preserve the exercise name EXACTLY as the trainer said it. Do not \
normalize, correct, or rephrase (e.g., keep "bench" as "bench", not \
"barbell bench press").
4. Expand set shorthand into individual records. "3 sets of 10 at 80 kilos" \
becomes 3 set entries, each with reps=10, weight=80, weight_unit="kg".
5. If a set range is given (e.g., "sets 2 through 4 at RPE 8"), create \
individual set entries for each set in the range.
6. Record weight exactly as spoken with the correct unit. Do not convert \
between kg and lbs. If no weight is mentioned at all, OMIT the weight and \
weight_unit fields entirely — do NOT assume "bodyweight", "BW", 0, or any \
default. A missing weight means the trainer chose not to state one.
7. NEVER invent, embellish, or add ANY information not explicitly stated in \
the transcript. This applies to everything: reps, weight, RPE, exercise names, \
observation text, flag reasons — all of it. If the trainer says "he feels \
great today", record exactly that meaning. Do NOT add symptoms, history, or \
context the trainer did not mention. EXCEPTION: when the trainer says "same", \
"same thing", "everything the same", "same as before", or similar — look at \
the session context and replicate the NUMERIC data from the previous set \
(reps, weight, weight_unit, rpe, rir). Do NOT copy over `notes` — notes are \
specific to the set they were recorded on. "Same" means same prescription, \
not same notes.
8. If the transcript is ambiguous, unclear, or contains no recognizable \
training content, create an observation card with flag_color="clarification" \
explaining what was unclear. Do NOT create exercise cards for words that are \
obviously not exercises (e.g., random words, names, non-fitness phrases). A \
valid exercise card requires a plausible exercise name — something that could \
reasonably be a gym exercise, sport movement, or physical activity. When in \
doubt between creating a dubious exercise card and flagging as clarification, \
always flag as clarification.
9. A single transcript may produce multiple tool calls — for example, one \
exercise card and one observation card, or multiple exercise cards.
10. Ignore filler words, false starts, and speech artifacts. Focus on the \
meaningful content.
11. If session context is provided, check whether the transcript refers to \
an existing entry before creating a new one. Use modify_exercise_card when \
the trainer is adding to or correcting a previously recorded exercise \
(e.g., "also RPE 8 on those", "no wait, 85 not 80").
12. Only call modify_exercise_card when session context is present. If no \
context is provided, always use record_exercise_card or \
record_observation_card.
13. When the transcript references an exercise but the reference is \
ambiguous (e.g., context has two similar exercises and it is unclear which \
one the trainer means), create an observation card with \
flag_color="clarification" explaining the ambiguity rather than guessing \
which entry to modify.
14. modify_exercise_card only targets exercise cards. To update or amend an \
observation, record a new observation card.
15. Use action="correct" ONLY when the trainer explicitly signals a \
correction (e.g., "no wait", "actually", "I meant", "that was wrong"). \
Default to action="add" for any other modification. Never overwrite \
existing data unless the trainer clearly intends to replace it.
16. If the trainer says "RIR 2", "2 reps in reserve", "could do 2 more", \
or "had 2 left", extract as the `rir` field on the set. Do NOT convert \
to RPE — record the raw RIR value.
17. Equipment modifications like "with a band", "added chains", "used \
straps" mean the same exercise with a different setup — NOT a new card. \
Record as `equipment_note` on the relevant sets. For example, "set 3 \
with a red band" is one exercise card with equipment_note on set 3.
18. Phrases like "correction, change X to Y", "that should be", "let me \
fix that" are structured corrections. Use modify_exercise_card with \
action="correct". This extends Rule 15's casual correction handling.
19. Standalone observations — anything the trainer says BETWEEN exercises \
or as a general check-in — are session-level with NO target_entry_id. \
This includes client state ("energy dropping", "looking fatigued"), pain \
complaints not embedded in set data ("his lower back is hurting", "knee \
feels off"), and check-in questions ("how are you feeling?"). Even if the \
complaint seems related to a recent exercise, do NOT infer the connection \
— the trainer would explicitly name the exercise if they meant to link it \
(e.g., "lower back hurting from those deadlifts"). If they just say "lower \
back is hurting" without naming an exercise, it's session-level.
20. When a trainer batches missed recordings (e.g., "bench press, first \
set 60kg 10 reps, second set 60kg 8 reps"), create ONE exercise card \
with multiple sets. Look for sequential set numbering as a signal that \
the trainer is recapping a single exercise, not separate exercises.
21. "Intensity" is a trainer synonym for RPE. If the trainer says \
"intensity seven" or "seven intensity", extract as rpe=7. Same for \
"perceived exertion" or "effort level."
22. When a trainer records additional sets for an already-logged exercise \
(e.g., "second set, 8 reps at 85"), use modify_exercise_card with \
action="add" and add_sets containing the new set(s). Do NOT create a new \
exercise_card for the same exercise. Look at the session context — if the \
exercise is already there, append to it.
23. Only set target_entry_id when the trainer EXPLICITLY names or clearly \
references a specific exercise in the same transcript (e.g., "left is \
tougher than right on the clamshells", "form broke down on the deadlift \
set 3"). Set attached_to_set when a specific set number is mentioned. \
If the transcript is a standalone comment with no exercise name, leave \
both fields empty — do not infer a connection from session context. If \
no context is provided, always leave both fields empty.
25. When the trainer mentions something about form, technique, or how a \
set felt (e.g., "good depth", "felt easy", "knees caving in", "grip \
slipped", "left shoulder tight"), put it as `notes` on the relevant \
set(s). Per-set `notes` appear in the set table next to RPE — this is \
the primary place for ALL commentary during an exercise. If the note \
applies to all sets ("good depth overall"), put it on every set.
26. For session-level observations (no target_entry_id), include temporal \
context by referencing what exercises have been completed so far. Instead \
of "energy levels are lower", write "energy levels dropping further after \
clamshells and squats." This makes the observation self-explanatory — a \
reader can see WHEN in the session it was noted without checking the \
timeline. Only do this when session context is available.
27. Write observation text as clean clinical notes, not verbatim speech. \
Strip filler words, self-references ("he's", "she mentioned", "that's \
what he's saying"), and conversational framing. "He's complaining of \
lower back pain" → "Lower back pain." "She said her knees feel weird" \
→ "Knee discomfort reported." "Energy levels are even lower now" → \
"Energy levels declining further." Write what a trainer would want to \
read in their notes later — concise, third-person, clinical.\
"""

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

# These are frozen (immutable) containers for parsed output. Once Claude
# extracts the data, it shouldn't be modified — it's a snapshot of what
# was said. Tuples instead of lists for the same reason.


@dataclass(frozen=True)
class ParsedSet:
    """A single set extracted from the transcript."""

    reps: int
    weight: float | None = None
    weight_unit: str | None = None
    rpe: float | None = None
    duration_seconds: int | None = None
    rir: float | None = None
    equipment_note: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class ParsedExerciseCard:
    """Structured exercise data extracted from a transcript."""

    exercise_name: str
    sets: tuple[ParsedSet, ...] | None = None
    form_notes: tuple[str, ...] = field(default_factory=tuple)
    cues_given: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ParsedObservationCard:
    """An observation extracted from a transcript.

    Can be session-level (no attachment) or exercise-specific
    (target_entry_id + optional attached_to_set).
    """

    observation_text: str
    flag_color: str | None = None
    flag_reason: str | None = None
    target_entry_id: int | None = None
    attached_to_set: int | None = None


@dataclass(frozen=True)
class ParsedModification:
    """A modification to an existing exercise card in the session.

    Represents the parser's instruction to update a previously recorded
    entry. The actual merge logic (applying updates to the stored entry)
    happens downstream in the endpoint layer.
    """

    target_entry_id: int
    action: str  # "add" or "correct"
    target_sets: tuple[int, ...] | None = None  # None = all sets
    updates: dict | None = None  # partial set fields: {"rpe": 8}
    add_sets: tuple[ParsedSet, ...] | None = None  # new sets to append
    form_notes: tuple[str, ...] = field(default_factory=tuple)
    cues_given: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ParserResult:
    """Complete result from parsing a transcript.

    Contains exercise cards (new), observation cards, modifications
    (updates to existing entries), and raw tool calls for debugging.
    """

    exercise_cards: tuple[ParsedExerciseCard, ...]
    observation_cards: tuple[ParsedObservationCard, ...]
    modifications: tuple[ParsedModification, ...] = field(default_factory=tuple)
    tool_call_order: tuple[str, ...] = field(default_factory=tuple)
    raw_tool_calls: tuple[dict, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "claude-sonnet-4-6"


def _build_exercise_card(tool_input: dict) -> ParsedExerciseCard:
    """Convert a record_exercise_card tool call input into a dataclass.

    Takes the raw dict from Claude's tool_use response (the "input" field)
    and maps it to a ParsedExerciseCard. Handles optional fields gracefully —
    if Claude didn't include sets, form_notes, or cues, they default to
    None/empty tuples.
    """
    sets = None
    if "sets" in tool_input and tool_input["sets"] is not None:
        parsed_sets = []
        for s in tool_input["sets"]:
            if not isinstance(s, dict):
                continue  # Skip null or non-dict entries
            if "reps" not in s:
                continue  # Skip malformed sets missing required reps field
            parsed_sets.append(
                ParsedSet(
                    reps=s["reps"],
                    weight=s.get("weight"),
                    weight_unit=s.get("weight_unit"),
                    rpe=s.get("rpe"),
                    duration_seconds=s.get("duration_seconds"),
                    rir=s.get("rir"),
                    equipment_note=s.get("equipment_note"),
                    notes=s.get("notes"),
                )
            )
        sets = tuple(parsed_sets) if parsed_sets else None

    return ParsedExerciseCard(
        exercise_name=tool_input["exercise_name"],
        sets=sets,
        form_notes=tuple(tool_input.get("form_notes", [])),
        cues_given=tuple(tool_input.get("cues_given", [])),
    )


def _build_observation_card(tool_input: dict) -> ParsedObservationCard:
    """Convert a record_observation_card tool call input into a dataclass."""
    return ParsedObservationCard(
        observation_text=tool_input["observation_text"],
        flag_color=tool_input.get("flag_color"),
        flag_reason=tool_input.get("flag_reason"),
        target_entry_id=tool_input.get("target_entry_id"),
        attached_to_set=tool_input.get("attached_to_set"),
    )


def _build_modification(tool_input: dict) -> ParsedModification:
    """Convert a modify_exercise_card tool call input into a dataclass."""
    target_sets = None
    if "target_sets" in tool_input and tool_input["target_sets"] is not None:
        target_sets = tuple(tool_input["target_sets"])

    add_sets = None
    if "add_sets" in tool_input and tool_input["add_sets"] is not None:
        parsed_sets = []
        for s in tool_input["add_sets"]:
            if not isinstance(s, dict) or "reps" not in s:
                continue
            parsed_sets.append(
                ParsedSet(
                    reps=s["reps"],
                    weight=s.get("weight"),
                    weight_unit=s.get("weight_unit"),
                    rpe=s.get("rpe"),
                    duration_seconds=s.get("duration_seconds"),
                    rir=s.get("rir"),
                    equipment_note=s.get("equipment_note"),
                    notes=s.get("notes"),
                )
            )
        add_sets = tuple(parsed_sets) if parsed_sets else None

    return ParsedModification(
        target_entry_id=tool_input["target_entry_id"],
        action=tool_input["action"],
        target_sets=target_sets,
        updates=tool_input.get("updates"),
        add_sets=add_sets,
        form_notes=tuple(tool_input.get("form_notes", [])),
        cues_given=tuple(tool_input.get("cues_given", [])),
    )


def _extract_parser_result(content_blocks: list[Any]) -> ParserResult:
    """Extract structured cards from Claude's response content blocks.

    Claude's response is a list of content blocks. Each block is either:
    - {"type": "text", "text": "..."} — we ignore these
    - {"type": "tool_use", "name": "record_exercise_card", "input": {...}}
    - {"type": "tool_use", "name": "record_observation_card", "input": {...}}
    - {"type": "tool_use", "name": "modify_exercise_card", "input": {...}}

    We iterate through the blocks, building cards/modifications from
    tool_use blocks and skipping everything else.
    """
    exercise_cards: list[ParsedExerciseCard] = []
    observation_cards: list[ParsedObservationCard] = []
    modifications: list[ParsedModification] = []
    tool_call_order: list[str] = []
    raw_tool_calls: list[dict] = []

    for block in content_blocks:
        if block.type != "tool_use":
            continue

        raw_tool_calls.append({"name": block.name, "input": block.input})

        try:
            if block.name == "record_exercise_card":
                exercise_cards.append(_build_exercise_card(block.input))
                tool_call_order.append("exercise")
            elif block.name == "record_observation_card":
                observation_cards.append(_build_observation_card(block.input))
                tool_call_order.append("observation")
            elif block.name == "modify_exercise_card":
                modifications.append(_build_modification(block.input))
                tool_call_order.append("modification")
        except (KeyError, TypeError):
            # Malformed tool input (e.g. empty dict missing required fields).
            # Skip the block — it's still captured in raw_tool_calls for debugging.
            continue

    return ParserResult(
        exercise_cards=tuple(exercise_cards),
        observation_cards=tuple(observation_cards),
        modifications=tuple(modifications),
        tool_call_order=tuple(tool_call_order),
        raw_tool_calls=tuple(raw_tool_calls),
    )


async def parse_transcript(
    transcript: str,
    *,
    session_context: list[dict] | None = None,
    model: str = DEFAULT_MODEL,
) -> ParserResult:
    """Parse a trainer's transcript into structured exercise and observation cards.

    Uses Claude's tool_use to extract structured data. The transcript is sent
    as a user message, and Claude responds by calling record_exercise_card,
    record_observation_card, and/or modify_exercise_card tools.

    When session_context is provided, prior entries are formatted and included
    in the user message so Claude can resolve references ("same weight",
    "RPE 8 on those") and decide whether to create new entries or modify
    existing ones.

    Args:
        transcript: The transcribed trainer speech to parse.
        session_context: Optional list of prior session entry dicts. Each dict
            should have 'entry_type' plus relevant fields. Entries are numbered
            [1], [2], etc. for Claude to reference.
        model: Claude model to use. Defaults to claude-sonnet-4-6.

    Returns:
        ParserResult with exercise cards, observation cards, and raw tool calls.

    Raises:
        ValueError: If transcript is empty or whitespace-only.
        anthropic.APIError: If the Claude API call fails.
    """
    if not transcript or not transcript.strip():
        raise ValueError("transcript must not be empty")

    # Build user message: context (if any) + transcript
    if session_context:
        context_block = format_session_context(session_context)
        user_content = f"{context_block}\n\nNew transcript to parse:\n{transcript}"
    else:
        user_content = transcript

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    response = await client.messages.create(
        model=model,
        max_tokens=1024,
        system=PARSER_SYSTEM_PROMPT,
        tools=PARSER_TOOLS,  # type: ignore[arg-type]  # SDK accepts plain dicts
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": user_content}],
    )

    return _extract_parser_result(response.content)
