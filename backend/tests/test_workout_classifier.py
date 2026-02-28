"""Tests for workout classification logic.

Uses real exercise_db.json data — no mocking needed since the classifier
is a pure function with no I/O beyond reading the bundled JSON file.
"""

import pytest

from app.services.workout_classifier import classify_workout


class TestClassifyWorkout:
    """Workout classification from exercise canonical names."""

    def test_pure_push_workout(self):
        """All chest/shoulder/tricep exercises → Upper Body Push."""
        exercises = [
            "Barbell Bench Press",
            "Incline Dumbbell Press",
            "Dumbbell Shoulder Press",
            "Close-Grip Bench Press",
        ]
        assert classify_workout(exercises) == "Upper Body Push"

    def test_pure_pull_workout(self):
        """All back/bicep exercises → Upper Body Pull."""
        exercises = [
            "Barbell Row",
            "Barbell Curl",
            "Face Pull",
            "Dumbbell Curl",
        ]
        assert classify_workout(exercises) == "Upper Body Pull"

    def test_pure_legs_workout(self):
        """All quad/glute/hamstring exercises → Lower Body."""
        exercises = [
            "Barbell Back Squat",
            "Barbell Hip Thrust",
            "Leg Press",
            "Romanian Deadlift",
        ]
        assert classify_workout(exercises) == "Lower Body"

    def test_mixed_push_pull(self):
        """Equal push and pull exercises → Upper Body."""
        exercises = [
            "Barbell Bench Press",
            "Overhead Press",
            "Barbell Row",
            "Barbell Curl",
        ]
        assert classify_workout(exercises) == "Upper Body"

    def test_full_body_mix(self):
        """Mix of push, pull, and legs → Full Body."""
        exercises = [
            "Barbell Bench Press",
            "Barbell Row",
            "Barbell Back Squat",
        ]
        assert classify_workout(exercises) == "Full Body"

    def test_empty_session(self):
        """No exercises → Session fallback."""
        assert classify_workout([]) == "Session"

    def test_unrecognized_exercises_fallback(self):
        """All exercises unknown to DB → Session fallback."""
        assert classify_workout(["Made Up Exercise", "Another Fake One"]) == "Session"

    def test_overhead_press_counts_as_push(self):
        """OHP has upper trapezius (pull) but is fundamentally push.

        The classifier uses dominant-region voting per exercise,
        so OHP's 3 push muscles outweigh the 1 pull muscle.
        """
        exercises = [
            "Overhead Press",
            "Overhead Press",
            "Overhead Press",
            "Overhead Press",
        ]
        assert classify_workout(exercises) == "Upper Body Push"

    def test_conditioning_workout(self):
        """All conditioning exercises → Conditioning."""
        exercises = [
            "Battle Ropes",
            "Assault Bike Sprint",
            "Kettlebell Swing",
        ]
        assert classify_workout(exercises) == "Conditioning"

    def test_core_dominant_workout(self):
        """All core exercises → Core."""
        exercises = [
            "Ab Wheel Rollout",
            "Pallof Press",
            "Ab Wheel Rollout",
        ]
        assert classify_workout(exercises) == "Core"

    def test_single_exercise(self):
        """One exercise is 100% dominant → its region."""
        assert classify_workout(["Barbell Back Squat"]) == "Lower Body"

    def test_case_insensitive_matching(self):
        """Exercise names should match case-insensitively."""
        exercises = [
            "barbell bench press",
            "incline dumbbell press",
            "dumbbell bench press",
        ]
        assert classify_workout(exercises) == "Upper Body Push"

    def test_at_threshold_boundary(self):
        """Exactly 70% same region (7/10 push) → should classify as that region."""
        exercises = [
            "Barbell Bench Press",
            "Incline Dumbbell Press",
            "Dumbbell Shoulder Press",
            "Overhead Press",
            "Floor Press",
            "Dip",
            "Push-Up",
            # 3 legs exercises to bring push to exactly 70%
            "Barbell Back Squat",
            "Bulgarian Split Squat",
            "Leg Press",
        ]
        assert classify_workout(exercises) == "Upper Body Push"

    def test_below_threshold(self):
        """67% same region (2/3 push, 1/3 legs) → falls through to Full Body."""
        exercises = [
            "Barbell Bench Press",
            "Dumbbell Shoulder Press",
            "Barbell Back Squat",
        ]
        assert classify_workout(exercises) == "Full Body"
