"""Live test: does Claude use target_entry_id and attached_to_set correctly?

Run with: cd backend && .venv/bin/python scripts/test_observation_attachment_live.py

Two scenarios from real trainer speech:

1. Set-specific pain: "third set deadlifts 12 reps slight lower back pain
   after seventh rep" — context has a deadlift entry with 2 sets already.
   Expected: observation attached to entry [1], set 3.

2. General client observation: "Pranav's complaining about his lower back"
   — said AFTER deadlifts are done, as a standalone comment.
   Expected: session-level observation, NO attachment.
"""

import asyncio
import json

from app.services.parser import parse_transcript


def _print_result(label: str, result):
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")

    if result.exercise_cards:
        for i, card in enumerate(result.exercise_cards):
            print(f"\n  Exercise Card {i + 1}:")
            print(f"    name: {card.exercise_name}")
            if card.sets:
                for j, s in enumerate(card.sets):
                    print(f"    set {j + 1}: {s}")

    if result.observation_cards:
        for i, card in enumerate(result.observation_cards):
            print(f"\n  Observation Card {i + 1}:")
            print(f"    text: {card.observation_text}")
            print(f"    flag_color: {card.flag_color}")
            print(f"    flag_reason: {card.flag_reason}")
            print(f"    target_entry_id: {card.target_entry_id}")
            print(f"    attached_to_set: {card.attached_to_set}")

    if result.modifications:
        for i, mod in enumerate(result.modifications):
            print(f"\n  Modification {i + 1}:")
            print(f"    target_entry_id: {mod.target_entry_id}")
            print(f"    action: {mod.action}")
            print(f"    target_sets: {mod.target_sets}")
            print(f"    updates: {mod.updates}")
            if mod.form_notes:
                print(f"    form_notes: {mod.form_notes}")

    print(f"\n  Raw tool calls:")
    for tc in result.raw_tool_calls:
        print(f"    {json.dumps(tc, indent=6)}")


async def main():
    # Context: deadlift entry with 2 sets already logged
    deadlift_context = [
        {
            "entry_type": "exercise_card",
            "exercise_name": "deadlifts",
            "sets": [
                {"reps": 10, "weight": 60, "weight_unit": "kg"},
                {"reps": 10, "weight": 60, "weight_unit": "kg"},
            ],
        },
    ]

    # -----------------------------------------------------------------
    # Scenario 1: Set-specific pain during exercise
    # "third set deadlifts 12 reps slight lower back pain after seventh rep"
    # Expected: modification/exercise update + observation attached to set 3
    # -----------------------------------------------------------------
    print("\n\nScenario 1: Set-specific pain during exercise")
    print("Transcript: 'third set deadlifts 12 reps slight lower back pain after seventh rep'")
    print(f"Context: {json.dumps(deadlift_context, indent=2)}")

    result1 = await parse_transcript(
        "third set deadlifts 12 reps slight lower back pain after seventh rep",
        session_context=deadlift_context,
    )
    _print_result("Scenario 1 Result", result1)

    # -----------------------------------------------------------------
    # Scenario 2: General observation after exercise
    # Context: deadlift with 3 sets complete, about to start next exercise
    # Trainer says: "Pranav's complaining about his lower back"
    # Expected: standalone observation, NO attachment
    # -----------------------------------------------------------------
    deadlift_context_3sets = [
        {
            "entry_type": "exercise_card",
            "exercise_name": "deadlifts",
            "sets": [
                {"reps": 10, "weight": 60, "weight_unit": "kg"},
                {"reps": 10, "weight": 60, "weight_unit": "kg"},
                {"reps": 12, "weight": 60, "weight_unit": "kg"},
            ],
        },
    ]

    print("\n\nScenario 2: General client observation after exercise")
    print("Transcript: 'Pranav is complaining about his lower back'")
    print(f"Context: {json.dumps(deadlift_context_3sets, indent=2)}")

    result2 = await parse_transcript(
        "Pranav is complaining about his lower back",
        session_context=deadlift_context_3sets,
    )
    _print_result("Scenario 2 Result", result2)

    # -----------------------------------------------------------------
    # Scenario 3: Exercise-specific observation (not set-specific)
    # "left glute was painful a bit on the clamshells"
    # Expected: observation attached to clamshell entry, no specific set
    # -----------------------------------------------------------------
    clamshell_context = [
        {
            "entry_type": "exercise_card",
            "exercise_name": "clamshells",
            "sets": [
                {"reps": 15},
                {"reps": 15},
            ],
        },
    ]

    print("\n\nScenario 3: Exercise-level observation (no specific set)")
    print("Transcript: 'left glute was a bit painful on the clamshells'")
    print(f"Context: {json.dumps(clamshell_context, indent=2)}")

    result3 = await parse_transcript(
        "left glute was a bit painful on the clamshells",
        session_context=clamshell_context,
    )
    _print_result("Scenario 3 Result", result3)

    # -----------------------------------------------------------------
    # Scenario 4: No context — should NOT guess attachment
    # -----------------------------------------------------------------
    print("\n\nScenario 4: No context — observation should have no attachment")
    print("Transcript: 'left glute was a bit painful'")
    print("Context: None")

    result4 = await parse_transcript(
        "left glute was a bit painful",
    )
    _print_result("Scenario 4 Result", result4)

    # -----------------------------------------------------------------
    # Scenario 5: Mid-session energy check-in (temporal context)
    # After clamshells and squats, trainer says "energy levels are lower"
    # Expected: session-level (no attachment), but observation text should
    # reference the preceding exercises for temporal context.
    # -----------------------------------------------------------------
    mid_session_context = [
        {
            "entry_type": "exercise_card",
            "exercise_name": "clamshells",
            "sets": [{"reps": 15}, {"reps": 15}],
        },
        {
            "entry_type": "exercise_card",
            "exercise_name": "squats",
            "sets": [
                {"reps": 10, "weight": 60, "weight_unit": "kg"},
                {"reps": 10, "weight": 60, "weight_unit": "kg"},
                {"reps": 10, "weight": 60, "weight_unit": "kg"},
            ],
        },
    ]

    print("\n\nScenario 5: Mid-session energy check-in (temporal context)")
    print("Transcript: 'energy levels are even lower now'")
    print(f"Context: {json.dumps(mid_session_context, indent=2)}")

    result5 = await parse_transcript(
        "energy levels are even lower now",
        session_context=mid_session_context,
    )
    _print_result("Scenario 5 Result", result5)

    # -----------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------
    print("\n\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)

    def _check_obs(result, label, expect_target, expect_set):
        obs = [c for c in result.observation_cards]
        if not obs:
            print(f"  {label}: NO observation card produced")
            return
        card = obs[0]
        target_ok = (card.target_entry_id is not None) == expect_target
        set_ok = (card.attached_to_set is not None) == expect_set
        status = "PASS" if (target_ok and set_ok) else "FAIL"
        print(
            f"  {label}: {status} | "
            f"target_entry_id={'set' if card.target_entry_id else 'empty'} "
            f"(expect {'set' if expect_target else 'empty'}) | "
            f"attached_to_set={'set' if card.attached_to_set else 'empty'} "
            f"(expect {'set' if expect_set else 'empty'})"
        )

    _check_obs(result1, "Scenario 1 (set-specific pain)", True, True)
    _check_obs(result2, "Scenario 2 (general complaint)", False, False)
    _check_obs(result3, "Scenario 3 (exercise-level)", True, False)
    _check_obs(result4, "Scenario 4 (no context)", False, False)
    _check_obs(result5, "Scenario 5 (mid-session energy)", False, False)

    # Scenario 5 special check: observation text should reference exercises
    if result5.observation_cards:
        text = result5.observation_cards[0].observation_text.lower()
        has_exercise_ref = "clamshell" in text or "squat" in text
        print(
            f"\n  Scenario 5 temporal context: "
            f"{'PASS' if has_exercise_ref else 'FAIL'} | "
            f"text references exercises: {has_exercise_ref}\n"
            f"    actual text: \"{result5.observation_cards[0].observation_text}\""
        )

    print()


if __name__ == "__main__":
    asyncio.run(main())
