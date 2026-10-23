"""Tests for the pieces of the session summary prompt (no database, no Claude)."""

from datetime import datetime, timezone

from app.models import Client, Session, SessionEntry
from app.services.session_summary import build_summary_prompt, describe_entry, format_sets

T0 = datetime(2026, 3, 2, 10, 0, 0, tzinfo=timezone.utc)
KNEE_NOTE = {"entry_type": "observation_card", "observation_text": "Knees caved in on the last squat set."}


def test_format_sets_covers_time_rpe_and_notes():
    entry = SessionEntry(sets=[
        {"reps": 1, "duration_seconds": 45},
        {"reps": 8, "weight": 30, "weight_unit": "kg", "notes": "Hamstrings felt tight"},
        {"reps": 12},
    ])
    assert format_sets(entry) == "1 set of 45s; 1 set of 8 reps at 30kg (Hamstrings felt tight); 1 set of 12 reps"


def test_format_sets_without_sets():
    assert format_sets(SessionEntry(sets=None)) == "no sets recorded"


def test_prompt_without_goals_or_injuries_says_so():
    db_client = Client(name="Sam Lee", goals=None, injury_history=None)
    session = Session(started_at=T0, duration_minutes=None)
    prompt = build_summary_prompt(db_client, session, [SessionEntry(**KNEE_NOTE)], {})
    assert "Goals: not recorded" in prompt
    assert "Injury history: none recorded" in prompt
    assert "Session length" not in prompt


def test_describe_entry_includes_form_notes_and_cues():
    entry = SessionEntry(
        entry_type="exercise_card", exercise_canonical="Goblet Squat",
        sets=[{"reps": 10, "weight": 16, "weight_unit": "kg"}],
        form_notes=["Heels lifting"], cues_given=["Knees out"],
    )
    assert describe_entry(entry) == "Goblet Squat: 1 set of 10 reps at 16kg. Form notes: Heels lifting. Cues (timing not recorded): Knees out"


def test_describe_entry_falls_back_to_the_spoken_name():
    entry = SessionEntry(entry_type="exercise_card", exercise_name="sled push", sets=[{"reps": 4}])
    assert describe_entry(entry) == "sled push: 1 set of 4 reps"


def test_describe_note_says_which_set_it_was_logged_against():
    entry = SessionEntry(entry_type="observation_card", observation_text="Knees caved in.", attached_to_set=3)
    assert describe_entry(entry) == "Note: Knees caved in. (logged against set 3)"
    assert describe_entry(SessionEntry(entry_type="observation_card", observation_text="Low energy.")) == "Note: Low energy."


def test_previous_best_is_only_marked_on_exercises_that_have_one():
    db_client = Client(name="Sam Lee")
    squat = SessionEntry(entry_type="exercise_card", exercise_canonical="Goblet Squat", sets=[{"reps": 10, "weight": 20}])
    rdl = SessionEntry(entry_type="exercise_card", exercise_canonical="Romanian Deadlift", sets=[{"reps": 8, "weight": 30}])
    prompt = build_summary_prompt(db_client, Session(started_at=T0), [squat, rdl], {"Goblet Squat": 18})
    assert "- Goblet Squat: 1 set of 10 reps at 20kg [previous best: 18]" in prompt
    assert "- Romanian Deadlift: 1 set of 8 reps at 30kg\n" in prompt + "\n"


def test_format_sets_reads_weight_kg_from_older_sets():
    """Seeded and older sets store weight_kg instead of weight + weight_unit."""
    entry = SessionEntry(sets=[{"set": 1, "weight_kg": 8.0, "reps": 8, "rpe": 5}, {"reps": 8, "weight": 17.5, "weight_unit": "lbs"}])
    assert format_sets(entry) == "1 set of 8 reps at 8kg, RPE 5; 1 set of 8 reps at 17.5lbs"


def test_set_weight_prefers_weight_and_handles_zero_and_missing():
    from app.services.session_summary import set_weight
    assert set_weight({"weight": 0, "weight_kg": 10}) == (0, "kg")
    assert set_weight({"weight_kg": 0}) == (0, "kg")
    assert set_weight({"reps": 5}) is None


def test_format_sets_groups_identical_sets_in_a_row():
    row = {"reps": 12, "weight_kg": 20}
    entry = SessionEntry(sets=[row, row, row, {"reps": 10, "weight_kg": 20}, row])
    assert format_sets(entry) == "3 sets of 12 reps at 20kg; 1 set of 10 reps at 20kg; 1 set of 12 reps at 20kg"
