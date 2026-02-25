"""Comprehensive tests for the exercise database.

Validates the rebuilt 142-exercise database against the old 97-exercise
baseline, stress-tests real trainer speech patterns, and verifies
structural integrity and Deepgram keyterm coverage.
"""

import json

import pytest

from app.services.transcription import (
    GYM_TERMS,
    KEYTERM_LIMIT,
    build_keyterm_list,
    load_exercise_db,
)


# ---------------------------------------------------------------------------
# Fixtures + helpers
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def exercises() -> list[dict]:
    """Load the exercise database once for the entire test module."""
    return load_exercise_db()


def find_exercise(query: str, exercises: list[dict]) -> str | None:
    """Case-insensitive exact match against canonical_name + all aliases.

    Returns the canonical_name if found, None otherwise. Simulates
    "can our system find this exercise when a trainer says X?"
    """
    q = query.lower()
    for exercise in exercises:
        if exercise["canonical_name"].lower() == q:
            return exercise["canonical_name"]
        for alias in exercise["aliases"]:
            if alias.lower() == q:
                return exercise["canonical_name"]
    return None


# ---------------------------------------------------------------------------
# Old DB baseline constants (measured from the 97-exercise auto-generated DB)
# ---------------------------------------------------------------------------

OLD_EXERCISE_COUNT = 97
OLD_TOTAL_ALIASES = 321
OLD_AVG_ALIASES = 3.3
OLD_MIN_ALIASES = 1
OLD_COMMON_ERRORS_TOTAL = 210
OLD_UNIQUE_MUSCLES = 55


# ===================================================================
# Class 1: Comparative Metrics
# ===================================================================


class TestComparativeMetrics:
    """Compare the new DB against hardcoded old-DB constants."""

    def test_exercise_count_increased(self, exercises: list[dict]) -> None:
        assert len(exercises) == 142
        assert len(exercises) > OLD_EXERCISE_COUNT

    def test_total_alias_coverage_massively_improved(self, exercises: list[dict]) -> None:
        total_aliases = sum(len(e["aliases"]) for e in exercises)
        assert total_aliases == 3466
        assert total_aliases > OLD_TOTAL_ALIASES * 10  # 10x+ improvement

    def test_average_alias_density(self, exercises: list[dict]) -> None:
        avg = sum(len(e["aliases"]) for e in exercises) / len(exercises)
        assert avg >= 20, f"Average alias density {avg:.1f} is below 20"

    def test_minimum_alias_floor(self, exercises: list[dict]) -> None:
        for exercise in exercises:
            count = len(exercise["aliases"])
            assert count >= 16, (
                f"{exercise['canonical_name']} has only {count} aliases (min is 16)"
            )

    def test_common_errors_consistent_depth(self, exercises: list[dict]) -> None:
        for exercise in exercises:
            count = len(exercise.get("common_errors", {}))
            assert 4 <= count <= 6, (
                f"{exercise['canonical_name']} has {count} common errors (expected 4-6)"
            )

    def test_muscle_specificity_improved(self, exercises: list[dict]) -> None:
        all_muscles: set[str] = set()
        for exercise in exercises:
            all_muscles.update(exercise.get("primary_muscles", []))
            all_muscles.update(exercise.get("secondary_muscles", []))
        assert len(all_muscles) >= 100, (
            f"Only {len(all_muscles)} unique muscle terms (need >=100, old had {OLD_UNIQUE_MUSCLES})"
        )

    def test_no_generic_muscle_groups(self, exercises: list[dict]) -> None:
        """Generic terms like 'chest' or 'back' should never appear as muscle names.

        The new DB uses specific anatomy: 'pectoralis major' not 'chest',
        'latissimus dorsi' not 'back', etc.
        """
        generic_terms = {"core", "chest", "back", "shoulders", "glutes", "legs", "arms"}
        all_muscles: set[str] = set()
        for exercise in exercises:
            all_muscles.update(exercise.get("primary_muscles", []))
            all_muscles.update(exercise.get("secondary_muscles", []))
        found = generic_terms & all_muscles
        assert not found, f"Generic muscle terms still in DB: {found}"

    def test_categories_normalized(self, exercises: list[dict]) -> None:
        valid_categories = {"compound", "isolation", "bodyweight", "plyometric", "conditioning"}
        actual = {e["category"] for e in exercises}
        assert actual == valid_categories, (
            f"Expected exactly {valid_categories}, got {actual}"
        )


# ===================================================================
# Class 2: Trainer Speech Recognition
# ===================================================================


class TestTrainerSpeechRecognition:
    """Verify real trainer phrases resolve to the correct exercise.

    These tests simulate what happens when a trainer says something
    and our system needs to match it to an exercise in the database.
    """

    def test_common_abbreviations(self, exercises: list[dict]) -> None:
        cases = {
            "RDL": "Romanian Deadlift",
            "OHP": "Overhead Press",
            "BSS": "Bulgarian Split Squat",
            "NHC": "Nordic Hamstring Curl",
            "TKE": "Terminal Knee Extension",
            "FS": "Front Squat",
            "BB curl": "Barbell Curl",
            "DB RDL": "Romanian Deadlift",
            "IDC": "Incline Dumbbell Curl",
        }
        for phrase, expected in cases.items():
            result = find_exercise(phrase, exercises)
            assert result == expected, f"'{phrase}' → {result}, expected {expected}"

    def test_nicknames_and_slang(self, exercises: list[dict]) -> None:
        cases = {
            "nordics": "Nordic Hamstring Curl",
            "the Arnold": "Arnold Press",
            "good mornings": "Good Morning",
            "Arnie press": "Arnold Press",
            "Meadows row": "T-Bar Row",
        }
        for phrase, expected in cases.items():
            result = find_exercise(phrase, exercises)
            assert result == expected, f"'{phrase}' → {result}, expected {expected}"

    def test_equipment_prefixed_names(self, exercises: list[dict]) -> None:
        cases = {
            "dumbbell bench press": "Dumbbell Bench Press",
            "cable fly": "Cable Chest Fly",
            "cable crunch": "Cable Crunch",
            "barbell curl": "Barbell Curl",
            "cable row": "Seated Cable Row",
            "trap bar deadlift": "Trap Bar Deadlift",
        }
        for phrase, expected in cases.items():
            result = find_exercise(phrase, exercises)
            assert result == expected, f"'{phrase}' → {result}, expected {expected}"

    def test_plural_and_verb_forms(self, exercises: list[dict]) -> None:
        cases = {
            "walking lunges": "Walking Lunge",
            "pull-ups": "Pull-Up",
            "dips": "Dip",
            "spider curls": "Spider Curl",
            "hip thrust": "Barbell Hip Thrust",
            "farmer's walk": "Farmer's Carry",
            "farmers walk": "Farmer's Carry",
            "farmer carry": "Farmer's Carry",
        }
        for phrase, expected in cases.items():
            result = find_exercise(phrase, exercises)
            assert result == expected, f"'{phrase}' → {result}, expected {expected}"

    def test_new_exercises_not_in_old_db(self, exercises: list[dict]) -> None:
        """These exercises didn't exist in the old 97-exercise DB."""
        new_exercises = [
            "suitcase carry",
            "Copenhagen plank",
            "spider curl",
            "drag curl",
            "bird dog row",
            "prowler sprint",
            "depth jump",
            "lateral bound",
            "Zottman curl",
            "assault bike",
            "power clean",
            "hang clean",
            "Spanish squat",
        ]
        for phrase in new_exercises:
            result = find_exercise(phrase, exercises)
            assert result is not None, (
                f"'{phrase}' not found — should exist in new DB"
            )

    def test_deep_aliases_new_db_only(self, exercises: list[dict]) -> None:
        """Aliases that only exist because of the deep research rebuild."""
        cases = {
            "ATG squat": "Barbell Back Squat",
            "pause squat": "Barbell Back Squat",
            "Anderson squat": "Barbell Back Squat",
            "deficit deadlift": "Conventional Deadlift",
            "rack pull": "Conventional Deadlift",
            "stiff-leg deadlift": "Romanian Deadlift",
            "touch-and-go deadlift": "Conventional Deadlift",
            "SSB squat": "Barbell Back Squat",
            "safety squat bar squat": "Barbell Back Squat",
            "goblet lunge": "Walking Lunge",
        }
        for phrase, expected in cases.items():
            result = find_exercise(phrase, exercises)
            assert result == expected, f"'{phrase}' → {result}, expected {expected}"

    def test_exercises_that_should_not_match(self, exercises: list[dict]) -> None:
        """These terms are intentionally not in our database."""
        non_exercises = ["jumping jacks", "burpee", "Zercher squat", "Jefferson deadlift"]
        for phrase in non_exercises:
            result = find_exercise(phrase, exercises)
            assert result is None, (
                f"'{phrase}' unexpectedly matched '{result}' — should not be in DB"
            )

    def test_case_insensitivity(self, exercises: list[dict]) -> None:
        """Lookup should be case-insensitive for all variations."""
        for variant in ["rdl", "RDL", "Rdl", "rDl"]:
            result = find_exercise(variant, exercises)
            assert result == "Romanian Deadlift", (
                f"'{variant}' → {result}, expected 'Romanian Deadlift'"
            )

    def test_skull_crusher_exact_name(self, exercises: list[dict]) -> None:
        """'skull crusher' (singular) should match, with equipment-prefixed variants."""
        assert find_exercise("skull crusher", exercises) == "Skull Crusher"
        assert find_exercise("Skull Crusher", exercises) == "Skull Crusher"
        assert find_exercise("barbell skull crusher", exercises) == "Skull Crusher"
        assert find_exercise("EZ bar skull crusher", exercises) == "Skull Crusher"

    def test_db_bench_press_variant(self, exercises: list[dict]) -> None:
        """DB bench press should resolve to Dumbbell Bench Press."""
        assert find_exercise("DB bench press", exercises) == "Dumbbell Bench Press"
        assert find_exercise("dumbbell bench press", exercises) == "Dumbbell Bench Press"

    def test_ghd_aliases(self, exercises: list[dict]) -> None:
        """GHD-prefixed aliases should resolve to the right exercises."""
        assert find_exercise("GHD extension", exercises) == "GHD Hip Extension"
        assert find_exercise("GHD back extension", exercises) == "Back Extension"
        assert find_exercise("GHD hyper", exercises) == "GHD Hip Extension"


# ===================================================================
# Class 3: Structural Quality
# ===================================================================


class TestStructuralQuality:
    """Validate data integrity of the full 142-exercise database."""

    REQUIRED_FIELDS = {
        "canonical_name",
        "aliases",
        "category",
        "primary_muscles",
        "secondary_muscles",
        "equipment",
        "difficulty",
        "common_errors",
    }

    def test_all_exercises_have_required_fields(self, exercises: list[dict]) -> None:
        for exercise in exercises:
            missing = self.REQUIRED_FIELDS - set(exercise.keys())
            assert not missing, (
                f"{exercise.get('canonical_name', 'UNKNOWN')} missing: {missing}"
            )

    def test_no_duplicate_canonical_names(self, exercises: list[dict]) -> None:
        names = [e["canonical_name"] for e in exercises]
        seen: set[str] = set()
        duplicates: list[str] = []
        for name in names:
            if name in seen:
                duplicates.append(name)
            seen.add(name)
        assert not duplicates, f"Duplicate canonical names: {duplicates}"

    def test_no_shared_aliases_between_exercises(self, exercises: list[dict]) -> None:
        alias_owners: dict[str, str] = {}
        conflicts: list[tuple[str, str, str]] = []
        for exercise in exercises:
            for alias in exercise["aliases"]:
                key = alias.lower()
                if key in alias_owners:
                    conflicts.append((alias, alias_owners[key], exercise["canonical_name"]))
                else:
                    alias_owners[key] = exercise["canonical_name"]
        assert not conflicts, (
            f"Shared aliases: {[(a, e1, e2) for a, e1, e2 in conflicts[:5]]}"
        )

    def test_no_alias_matches_another_canonical_name(self, exercises: list[dict]) -> None:
        canonical_set = {e["canonical_name"].lower() for e in exercises}
        conflicts: list[tuple[str, str]] = []
        for exercise in exercises:
            for alias in exercise["aliases"]:
                if (
                    alias.lower() in canonical_set
                    and alias.lower() != exercise["canonical_name"].lower()
                ):
                    conflicts.append((alias, exercise["canonical_name"]))
        assert not conflicts, (
            f"Aliases matching other canonical names: {conflicts[:5]}"
        )

    def test_all_aliases_are_nonempty_trimmed_strings(self, exercises: list[dict]) -> None:
        for exercise in exercises:
            for alias in exercise["aliases"]:
                assert isinstance(alias, str), (
                    f"{exercise['canonical_name']}: alias {alias!r} is not a string"
                )
                assert alias.strip(), (
                    f"{exercise['canonical_name']}: empty/blank alias found"
                )
                assert alias == alias.strip(), (
                    f"{exercise['canonical_name']}: alias {alias!r} has leading/trailing whitespace"
                )

    def test_valid_categories_only(self, exercises: list[dict]) -> None:
        valid = {"compound", "isolation", "bodyweight", "plyometric", "conditioning"}
        for exercise in exercises:
            assert exercise["category"] in valid, (
                f"{exercise['canonical_name']}: invalid category '{exercise['category']}'"
            )

    def test_valid_difficulties_only(self, exercises: list[dict]) -> None:
        valid = {"beginner", "intermediate", "advanced"}
        for exercise in exercises:
            assert exercise["difficulty"] in valid, (
                f"{exercise['canonical_name']}: invalid difficulty '{exercise['difficulty']}'"
            )

    def test_common_errors_are_substantive(self, exercises: list[dict]) -> None:
        """Error keys should be non-empty, values should be real coaching content (>=50 chars)."""
        for exercise in exercises:
            errors = exercise.get("common_errors", {})
            for key, value in errors.items():
                assert key.strip(), (
                    f"{exercise['canonical_name']}: empty error key"
                )
                assert len(value) >= 50, (
                    f"{exercise['canonical_name']}: error '{key}' is only "
                    f"{len(value)} chars — expected real coaching content (>=50)"
                )

    def test_primary_muscles_nonempty(self, exercises: list[dict]) -> None:
        for exercise in exercises:
            muscles = exercise.get("primary_muscles", [])
            assert len(muscles) >= 1, (
                f"{exercise['canonical_name']}: no primary muscles listed"
            )

    def test_equipment_nonempty(self, exercises: list[dict]) -> None:
        for exercise in exercises:
            equipment = exercise.get("equipment", [])
            assert len(equipment) >= 1, (
                f"{exercise['canonical_name']}: no equipment listed"
            )

    def test_exercises_sorted_alphabetically(self, exercises: list[dict]) -> None:
        names = [e["canonical_name"] for e in exercises]
        assert names == sorted(names), "Exercises are not sorted alphabetically"

    def test_no_duplicate_aliases_within_exercise(self, exercises: list[dict]) -> None:
        for exercise in exercises:
            seen: set[str] = set()
            duplicates: list[str] = []
            for alias in exercise["aliases"]:
                key = alias.lower()
                if key in seen:
                    duplicates.append(alias)
                seen.add(key)
            assert not duplicates, (
                f"{exercise['canonical_name']}: duplicate aliases {duplicates}"
            )


# ===================================================================
# Class 4: Keyterm Coverage
# ===================================================================


class TestKeytermCoverage:
    """Verify the Deepgram keyterm builder works well with the expanded DB."""

    @pytest.fixture(scope="class")
    def keyterms(self) -> list[str]:
        return build_keyterm_list()

    def test_keyterms_at_100_capacity(self, keyterms: list[str]) -> None:
        assert len(keyterms) == KEYTERM_LIMIT, (
            f"Expected all {KEYTERM_LIMIT} keyterm slots filled, got {len(keyterms)}"
        )

    def test_gym_jargon_always_included(self, keyterms: list[str]) -> None:
        keyterm_set = set(keyterms)
        for term in ["RPE", "AMRAP", "EMOM"]:
            assert term in keyterm_set, f"Gym jargon '{term}' missing from keyterms"

    def test_key_abbreviations_present(self, keyterms: list[str]) -> None:
        keyterm_set = set(keyterms)
        for abbrev in ["RDL", "OHP", "NHC"]:
            assert abbrev in keyterm_set, (
                f"Abbreviation '{abbrev}' missing from keyterms"
            )

    def test_common_single_words_excluded(self, keyterms: list[str]) -> None:
        keyterm_lower = {k.lower() for k in keyterms}
        for word in ["squat", "bench", "plank"]:
            assert word not in keyterm_lower, (
                f"Common word '{word}' should not be in keyterms"
            )

    def test_no_duplicate_keyterms(self, keyterms: list[str]) -> None:
        lowered = [k.lower() for k in keyterms]
        assert len(lowered) == len(set(lowered)), "Duplicate keyterms found"
