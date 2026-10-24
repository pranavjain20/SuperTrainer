"""Tests for how briefs map exercises and muscles to muscle groups."""

import pytest

from app.models import SessionEntry
from app.services.session_brief import muscle_group, resolve_exercise


@pytest.mark.parametrize("muscle,group", [
    ("biceps femoris long head", "hamstrings"),
    ("biceps brachii", "biceps"),
    ("rectus femoris", "quads"),
    ("rectus abdominis", "core"),
    ("gastrocnemius", "calves"),
    ("posterior deltoid", "shoulders"),
    ("flexor carpi radialis", None),
])
def test_muscle_group(muscle, group):
    assert muscle_group(muscle) == group


@pytest.mark.parametrize("stored,expected", [
    ("goblet_squat", "Goblet Squat"),  # seeded entries store snake_case
    ("Lat Pulldown", "Lat Pulldown"),
    ("Not An Exercise", None),
])
def test_resolve_exercise(stored, expected):
    entry = SessionEntry(entry_type="exercise_card", exercise_canonical=stored)
    assert resolve_exercise(entry) == expected
