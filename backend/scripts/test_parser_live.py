#!/usr/bin/env python3
"""Live parser test script — sends real transcripts to Claude API.

Not part of the test suite. For interactive prompt tuning with Pranav:
  1. Run this script
  2. Review each result
  3. Tweak PARSER_SYSTEM_PROMPT in parser.py
  4. Re-run and compare

Usage:
    cd backend
    python scripts/test_parser_live.py              # run all
    python scripts/test_parser_live.py 3 7          # run specific cases
    python scripts/test_parser_live.py --verbose     # show raw tool calls
"""

import asyncio
import json
import sys

# Add parent dir to path so we can import app modules
sys.path.insert(0, ".")

from app.services.parser import parse_transcript, format_session_context


# -----------------------------------------------------------------------
# Test cases: (label, transcript, session_context_or_None, expected_behavior)
#
# Cases 1-9: verbatim quotes from Pranav's trainer (2026-02-25 session)
# Cases 10-15: synthetic cases covering patterns the real transcript doesn't hit
# -----------------------------------------------------------------------

TEST_CASES: list[tuple[str, str, list[dict] | None, str]] = [
    # === REAL TRAINER QUOTES (from reference/session_transcript_2026-02-25.md) ===

    (
        "1. Pre-session energy observation",
        "Pranav hasn't slept well. Energy levels below baseline.",
        None,
        # Expected: observation card, possibly yellow flag for low energy.
        # No exercise context — this is a pre-session note.
        "EXPECT: observation_card (client energy/sleep note). Possibly yellow flag.",
    ),

    (
        "2. Body asymmetry observation (clamshells context)",
        "Left is tougher than right.",
        [{
            "entry_type": "exercise_card",
            "exercise_name": "clamshell",
            "sets": [{"reps": 12}],
        }],
        # Expected: observation card about body asymmetry.
        # Should NOT try to modify the exercise card — this is a qualitative note.
        "EXPECT: observation_card about left/right asymmetry. NOT a modify.",
    ),

    (
        "3. Trainer records set with RPE",
        "clamshell set two, 12 reps, RPE seven",
        [{
            "entry_type": "exercise_card",
            "exercise_name": "clamshell",
            "sets": [{"reps": 12}],
        }],
        # Trainer recording a completed set with RPE.
        # Context has set 1 already — this is set 2 being added.
        "EXPECT: modify_exercise_card [1] action='add', updates: {reps: 12, rpe: 7}.",
    ),

    (
        "4. Second set recap (trainer shorthand)",
        "second set of squats, we did 12 reps for 20 kgs",
        [{
            "entry_type": "exercise_card",
            "exercise_name": "squat",
            "sets": [{"reps": 12, "weight": 20, "weight_unit": "kg"}],
        }],
        # Expected: either modify (add set 2 to existing squat entry)
        # or new exercise card with one set. Modify preferred since context exists.
        "EXPECT: modify_exercise_card [1] action='add' with set: 12 reps, 20kg. "
        "Or new exercise_card 'squats' with 12 reps @ 20kg.",
    ),

    (
        "5. Set recap with equipment + observation (compound)",
        "set number three, same weight as previous, 12 reps, addition of band. "
        "And with that, engagement goes up, and there is more scope of resistance improvement.",
        [{
            "entry_type": "exercise_card",
            "exercise_name": "squat",
            "sets": [
                {"reps": 12, "weight": 20, "weight_unit": "kg"},
                {"reps": 12, "weight": 20, "weight_unit": "kg"},
            ],
        }],
        # KEY TEST: 'same weight as previous' — Claude needs context to resolve to 20kg.
        # 'addition of band' → equipment_note.
        # Second sentence is a standalone observation about engagement (Rule 19).
        "EXPECT: modify or new set: 20kg, 12 reps, equipment_note='band' (or similar). "
        "PLUS: observation_card about engagement/resistance improvement.",
    ),

    (
        "6. Mid-session energy observation (standalone)",
        "mid-session the energy levels are lower comparatively",
        [{
            "entry_type": "exercise_card",
            "exercise_name": "squat",
            "sets": [
                {"reps": 12, "weight": 20, "weight_unit": "kg"},
                {"reps": 12, "weight": 20, "weight_unit": "kg"},
                {"reps": 12, "weight": 20, "weight_unit": "kg"},
            ],
        },
        {
            "entry_type": "exercise_card",
            "exercise_name": "leg press",
            "sets": [{"reps": 10, "weight": 45, "weight_unit": "kg"}],
        }],
        # Expected: standalone observation card (Rule 19 — not attached to exercise).
        # Should NOT be a modification to either exercise.
        "EXPECT: observation_card (client state, mid-session energy drop). "
        "NOT a modify. Rule 19 applies.",
    ),

    (
        "7. New exercise + comparison observation (compound sentence)",
        "single legged leg press, 45 kgs for 10 reps. It was slightly more "
        "tougher compared to the last session",
        None,
        # KEY TEST: compound sentence — exercise data + comparison observation.
        # Expected: exercise_card (single leg leg press, 45kg, 10 reps)
        # PLUS observation_card about difficulty comparison.
        "EXPECT: exercise_card 'single legged leg press' (45kg, 10 reps) "
        "PLUS observation_card about comparison to last session.",
    ),

    (
        "8. RPE on specific set",
        "set number two, RPE eight",
        [{
            "entry_type": "exercise_card",
            "exercise_name": "leg press",
            "sets": [
                {"reps": 10, "weight": 45, "weight_unit": "kg"},
                {"reps": 10, "weight": 45, "weight_unit": "kg"},
            ],
        }],
        # Expected: modify entry [1], target_sets=[2], updates={rpe: 8}.
        "EXPECT: modify_exercise_card [1], target_sets=[2], updates: {rpe: 8}.",
    ),

    (
        "9. Set with equipment addition, same weight",
        "added red resistance band, same reps, same weight",
        [{
            "entry_type": "exercise_card",
            "exercise_name": "squat",
            "sets": [
                {"reps": 12, "weight": 20, "weight_unit": "kg"},
                {"reps": 12, "weight": 20, "weight_unit": "kg"},
            ],
        }],
        # Trainer recording a set where the only change is adding equipment.
        # "same reps, same weight" means 12 reps, 20kg (from context).
        # Should modify with equipment_note + resolved reps/weight from context.
        "EXPECT: modify_exercise_card [1] with reps=12, weight=20, "
        "equipment_note='red resistance band' or similar.",
    ),

    # === SYNTHETIC CASES (patterns not in the real transcript) ===

    (
        "10. Intensity as RPE synonym",
        "squat set one, 10 reps, intensity seven",
        [{
            "entry_type": "exercise_card",
            "exercise_name": "squat",
            "sets": [{"reps": 10, "weight": 60, "weight_unit": "kg"}],
        }],
        # KEY TEST: 'intensity' is a trainer synonym for RPE.
        # Should extract as rpe=7, NOT as a separate observation.
        "EXPECT: modify_exercise_card [1], updates: {rpe: 7}. "
        "KEY: 'intensity' must map to RPE.",
    ),

    (
        "11. RIR spoken explicitly",
        "squat 5 at 100 kilos RIR 2",
        None,
        "EXPECT: exercise_card 'squat' (5 reps, 100kg, rir=2). NOT rpe.",
    ),

    (
        "12. Structured correction",
        "correction, change third set bench press from 12 to 8",
        [{
            "entry_type": "exercise_card",
            "exercise_name": "bench press",
            "sets": [
                {"reps": 10, "weight": 80, "weight_unit": "kg"},
                {"reps": 10, "weight": 80, "weight_unit": "kg"},
                {"reps": 12, "weight": 80, "weight_unit": "kg"},
            ],
        }],
        "EXPECT: modify_exercise_card [1], action='correct', target_sets=[3], "
        "updates: {reps: 8}.",
    ),

    (
        "13. RIR + equipment together",
        "squats with a band, 3x10 at 60, RIR 3",
        None,
        "EXPECT: exercise_card 'squats' (3 sets, 10 reps, 60kg, rir=3, "
        "equipment_note='with a band' or similar on each set).",
    ),

    (
        "14. Catch-up batch recording",
        "bench press, first set 60kg 10 reps, second set 60kg 8 reps",
        None,
        "EXPECT: ONE exercise_card 'bench press' with 2 sets "
        "(set 1: 10 reps @ 60kg, set 2: 8 reps @ 60kg). Rule 20.",
    ),

    (
        "15. Additive set with context",
        "did one more set of bench, 80 for 5",
        [{
            "entry_type": "exercise_card",
            "exercise_name": "bench press",
            "sets": [
                {"reps": 10, "weight": 80, "weight_unit": "kg"},
                {"reps": 10, "weight": 80, "weight_unit": "kg"},
                {"reps": 10, "weight": 80, "weight_unit": "kg"},
            ],
        }],
        "EXPECT: modify_exercise_card [1], action='add', with new set "
        "(5 reps, 80kg).",
    ),
]


def _format_result(result, verbose: bool = False) -> str:
    """Pretty-print a ParserResult."""
    lines: list[str] = []

    for card in result.exercise_cards:
        sets_desc = "no sets"
        if card.sets:
            set_parts = []
            for s in card.sets:
                part = f"{s.reps} reps"
                if s.weight is not None:
                    part += f" @ {s.weight}{s.weight_unit or ''}"
                if s.rpe is not None:
                    part += f" RPE {s.rpe}"
                if s.rir is not None:
                    part += f" RIR {s.rir}"
                if s.equipment_note:
                    part += f" [{s.equipment_note}]"
                set_parts.append(part)
            sets_desc = ", ".join(set_parts)
        lines.append(f"  EXERCISE: {card.exercise_name} | {sets_desc}")
        if card.form_notes:
            lines.append(f"    form: {list(card.form_notes)}")
        if card.cues_given:
            lines.append(f"    cues: {list(card.cues_given)}")

    for obs in result.observation_cards:
        flag = f" ({obs.flag_color} flag: {obs.flag_reason})" if obs.flag_color else ""
        lines.append(f"  OBSERVATION: {obs.observation_text}{flag}")

    for mod in result.modifications:
        sets_str = f" sets={list(mod.target_sets)}" if mod.target_sets else " all sets"
        lines.append(f"  MODIFY [{mod.target_entry_id}] {mod.action}{sets_str}: {mod.updates}")
        if mod.form_notes:
            lines.append(f"    form: {list(mod.form_notes)}")

    if verbose:
        lines.append(f"  RAW: {json.dumps([dict(r) for r in result.raw_tool_calls], indent=2)}")

    return "\n".join(lines) if lines else "  (no tool calls)"


async def run_tests(indices: list[int] | None = None, verbose: bool = False) -> None:
    """Run test cases against live Claude API."""
    cases = TEST_CASES
    if indices:
        cases = [TEST_CASES[i - 1] for i in indices if 1 <= i <= len(TEST_CASES)]

    print(f"\n{'='*70}")
    print(f"Live parser test — {len(cases)} cases")
    print(f"{'='*70}\n")

    for label, transcript, context, expected in cases:
        print(f"--- {label} ---")
        print(f"  Transcript: \"{transcript}\"")
        if context:
            print(f"  Context: {format_session_context(context)}")
        print(f"  {expected}")
        print()

        try:
            result = await parse_transcript(transcript, session_context=context)
            print(_format_result(result, verbose=verbose))
        except Exception as e:
            print(f"  ERROR: {e}")

        print()


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--verbose"]
    verbose = "--verbose" in sys.argv

    indices = None
    if args:
        try:
            indices = [int(a) for a in args]
        except ValueError:
            print(f"Usage: {sys.argv[0]} [case_numbers...] [--verbose]")
            sys.exit(1)

    asyncio.run(run_tests(indices=indices, verbose=verbose))
