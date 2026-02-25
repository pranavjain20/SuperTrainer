"""Tests for the validation layer — exercise matching, weight normalization,
set validation, pain extraction, card validators, and orchestration."""

import pytest

from app.services.parser import (
    ParsedExerciseCard,
    ParsedModification,
    ParsedObservationCard,
    ParsedSet,
    ParserResult,
)
from app.services.validation import (
    DEFAULT_SEVERITY,
    ExerciseMatch,
    PainMention,
    ValidatedExerciseCard,
    ValidatedModification,
    ValidatedObservationCard,
    ValidatedSet,
    ValidationResult,
    ValidationWarning,
    build_exercise_lookup,
    calculate_total_volume,
    convert_rir_to_rpe,
    extract_pain_mentions,
    match_exercise_name,
    normalize_weight,
    validate_exercise_card,
    validate_modification,
    validate_observation_card,
    validate_parser_result,
    validate_set,
)


# ===================================================================
# convert_rir_to_rpe
# ===================================================================


class TestConvertRirToRpe:
    def test_rir_0_gives_rpe_10(self):
        assert convert_rir_to_rpe(0) == 10.0

    def test_rir_1_gives_rpe_9(self):
        assert convert_rir_to_rpe(1) == 9.0

    def test_rir_2_gives_rpe_8(self):
        assert convert_rir_to_rpe(2) == 8.0

    def test_rir_1_5_gives_rpe_8_5(self):
        assert convert_rir_to_rpe(1.5) == 8.5

    def test_rir_5_gives_rpe_5(self):
        assert convert_rir_to_rpe(5) == 5.0

    def test_rir_high_clamps_to_rpe_1(self):
        """RIR 10 → RPE 0 → clamped to 1.0."""
        assert convert_rir_to_rpe(10) == 1.0

    def test_rir_negative_clamps_to_rpe_10(self):
        """RIR -1 → RPE 11 → clamped to 10.0."""
        assert convert_rir_to_rpe(-1) == 10.0


# ===================================================================
# Test fixtures
# ===================================================================


@pytest.fixture
def small_exercise_db() -> list[dict]:
    """Small exercise DB for fast, deterministic tests."""
    return [
        {
            "canonical_name": "Barbell Bench Press",
            "aliases": ["bench press", "bench", "flat bench", "barbell bench"],
        },
        {
            "canonical_name": "Barbell Back Squat",
            "aliases": ["back squat", "squat", "barbell squat", "BB squat"],
        },
        {
            "canonical_name": "Romanian Deadlift",
            "aliases": ["RDL", "romanian deadlift", "stiff leg deadlift"],
        },
        {
            "canonical_name": "Lat Pulldown",
            "aliases": ["lat pulldown", "pulldown", "lat pull-down"],
        },
        {
            "canonical_name": "Dumbbell Lateral Raise",
            "aliases": ["lateral raise", "side raise", "DB lateral raise", "lat raise"],
        },
    ]


@pytest.fixture
def exercise_lookup(small_exercise_db) -> dict[str, str]:
    """Pre-built lookup from the small DB."""
    return build_exercise_lookup(small_exercise_db)


# ===================================================================
# build_exercise_lookup
# ===================================================================


class TestBuildExerciseLookup:
    def test_includes_canonical_names(self, small_exercise_db):
        lookup = build_exercise_lookup(small_exercise_db)
        assert "barbell bench press" in lookup
        assert lookup["barbell bench press"] == "Barbell Bench Press"

    def test_includes_aliases(self, small_exercise_db):
        lookup = build_exercise_lookup(small_exercise_db)
        assert "bench" in lookup
        assert lookup["bench"] == "Barbell Bench Press"

    def test_case_insensitive(self, small_exercise_db):
        lookup = build_exercise_lookup(small_exercise_db)
        assert "rdl" in lookup
        assert lookup["rdl"] == "Romanian Deadlift"

    def test_all_entries_present(self, small_exercise_db):
        lookup = build_exercise_lookup(small_exercise_db)
        # Unique entries after lowercasing — some aliases duplicate the
        # canonical name (e.g., "romanian deadlift" alias matches canonical).
        # Count unique lowercased keys manually: 21
        assert len(lookup) == 21

    def test_empty_db(self):
        lookup = build_exercise_lookup([])
        assert lookup == {}

    def test_missing_aliases_key(self):
        lookup = build_exercise_lookup([{"canonical_name": "Push-up"}])
        assert "push-up" in lookup
        assert len(lookup) == 1


# ===================================================================
# match_exercise_name
# ===================================================================


class TestMatchExerciseName:
    def test_exact_match_canonical(self, exercise_lookup):
        result = match_exercise_name("Barbell Bench Press", exercise_lookup)
        assert result is not None
        assert result.canonical_name == "Barbell Bench Press"
        assert result.confidence == 100

    def test_exact_match_alias(self, exercise_lookup):
        result = match_exercise_name("bench press", exercise_lookup)
        assert result is not None
        assert result.canonical_name == "Barbell Bench Press"
        assert result.confidence == 100

    def test_case_insensitive_match(self, exercise_lookup):
        result = match_exercise_name("BENCH PRESS", exercise_lookup)
        assert result is not None
        assert result.canonical_name == "Barbell Bench Press"
        assert result.confidence == 100

    def test_fuzzy_match_typo(self, exercise_lookup):
        result = match_exercise_name("benchh press", exercise_lookup)
        assert result is not None
        assert result.canonical_name == "Barbell Bench Press"
        assert result.confidence > 50

    def test_fuzzy_match_abbreviation(self, exercise_lookup):
        result = match_exercise_name("RDL", exercise_lookup)
        assert result is not None
        assert result.canonical_name == "Romanian Deadlift"
        assert result.confidence == 100  # exact alias match

    def test_no_match_below_cutoff(self, exercise_lookup):
        # WRatio can be generous — use high cutoff to test the mechanism
        result = match_exercise_name("xyzzy foobar nonsense", exercise_lookup, score_cutoff=60)
        assert result is None

    def test_empty_string(self, exercise_lookup):
        result = match_exercise_name("", exercise_lookup)
        assert result is None

    def test_whitespace_only(self, exercise_lookup):
        result = match_exercise_name("   ", exercise_lookup)
        assert result is None

    def test_partial_name_fuzzy(self, exercise_lookup):
        result = match_exercise_name("lat pulldown", exercise_lookup)
        assert result is not None
        assert result.canonical_name == "Lat Pulldown"

    def test_custom_cutoff(self, exercise_lookup):
        # Very high cutoff — only exact matches
        result = match_exercise_name("bnech presss", exercise_lookup, score_cutoff=95)
        assert result is None


# ===================================================================
# normalize_weight
# ===================================================================


class TestNormalizeWeight:
    def test_kg_passthrough(self):
        weight, unit, warnings = normalize_weight(80.0, "kg")
        assert weight == 80.0
        assert unit == "kg"
        assert warnings == []

    def test_lbs_conversion(self):
        weight, unit, warnings = normalize_weight(185.0, "lbs")
        assert weight == 83.9  # 185 * 0.453592 ≈ 83.91
        assert unit == "lbs"
        assert warnings == []

    def test_none_weight(self):
        weight, unit, warnings = normalize_weight(None, "kg")
        assert weight is None
        assert unit is None
        assert warnings == []

    def test_default_unit_kg(self):
        weight, unit, warnings = normalize_weight(100.0, None, default_unit="kg")
        assert weight == 100.0
        assert unit == "kg"
        assert warnings == []

    def test_default_unit_lbs(self):
        weight, unit, warnings = normalize_weight(100.0, None, default_unit="lbs")
        assert weight == 45.4  # 100 * 0.453592 ≈ 45.36
        assert unit == "lbs"
        assert warnings == []

    def test_rounds_to_one_decimal(self):
        weight, _, warnings = normalize_weight(83.333, "kg")
        assert weight == 83.3
        assert warnings == []

    def test_zero_weight(self):
        weight, unit, warnings = normalize_weight(0.0, "kg")
        assert weight == 0.0
        assert unit == "kg"
        assert warnings == []

    def test_unknown_unit_defaults_to_kg_with_warning(self):
        """Unknown unit (not 'kg' or 'lbs') → default to kg, emit warning."""
        weight, unit, warnings = normalize_weight(100.0, "stones")
        assert weight == 100.0
        assert unit == "kg"
        assert len(warnings) == 1
        assert warnings[0].code == "unknown_weight_unit"
        assert "stones" in warnings[0].message


# ===================================================================
# validate_set
# ===================================================================


class TestValidateSet:
    def test_valid_set_kg(self):
        validated, warnings = validate_set(
            {"reps": 10, "weight": 80.0, "weight_unit": "kg", "rpe": 8}
        )
        assert validated.reps == 10
        assert validated.weight_kg == 80.0
        assert validated.weight_original == 80.0
        assert validated.weight_unit_original == "kg"
        assert validated.rpe == 8
        assert warnings == []

    def test_valid_set_lbs_conversion(self):
        validated, warnings = validate_set(
            {"reps": 5, "weight": 225.0, "weight_unit": "lbs"}
        )
        assert validated.reps == 5
        assert validated.weight_kg == 102.1  # 225 * 0.453592
        assert validated.weight_original == 225.0
        assert validated.weight_unit_original == "lbs"
        assert warnings == []

    def test_missing_weight(self):
        validated, warnings = validate_set({"reps": 20})
        assert validated.reps == 20
        assert validated.weight_kg is None
        assert validated.weight_original is None
        assert warnings == []

    def test_default_weight_unit_applied(self):
        validated, warnings = validate_set(
            {"reps": 10, "weight": 100.0},
            default_weight_unit="lbs",
        )
        assert validated.weight_kg == 45.4
        assert validated.weight_unit_original == "lbs"

    def test_negative_reps_warning(self):
        validated, warnings = validate_set({"reps": -5, "weight": 80.0, "weight_unit": "kg"})
        assert len(warnings) == 1
        assert warnings[0].code == "invalid_reps"
        assert validated.reps == 1  # clamped to minimum

    def test_zero_reps_warning(self):
        validated, warnings = validate_set({"reps": 0})
        assert len(warnings) == 1
        assert warnings[0].code == "invalid_reps"

    def test_negative_weight_warning(self):
        validated, warnings = validate_set(
            {"reps": 10, "weight": -50.0, "weight_unit": "kg"}
        )
        assert len(warnings) == 1
        assert warnings[0].code == "negative_weight"
        assert validated.weight_kg == 50.0  # absolute value

    def test_rpe_out_of_range_high(self):
        validated, warnings = validate_set({"reps": 10, "rpe": 12})
        assert len(warnings) == 1
        assert warnings[0].code == "invalid_rpe"
        assert validated.rpe == 10  # clamped

    def test_rpe_out_of_range_low(self):
        validated, warnings = validate_set({"reps": 10, "rpe": 0})
        assert len(warnings) == 1
        assert warnings[0].code == "invalid_rpe"
        assert validated.rpe == 1  # clamped

    def test_valid_duration(self):
        validated, warnings = validate_set({"reps": 1, "duration_seconds": 60})
        assert validated.duration_seconds == 60
        assert warnings == []

    def test_invalid_duration(self):
        validated, warnings = validate_set({"reps": 1, "duration_seconds": -10})
        assert len(warnings) == 1
        assert warnings[0].code == "invalid_duration"

    def test_missing_reps_key(self):
        validated, warnings = validate_set({"weight": 80.0, "weight_unit": "kg"})
        assert len(warnings) == 1
        assert warnings[0].code == "invalid_reps"
        assert validated.reps == 1  # defaults to 1

    def test_multiple_warnings_combined(self):
        validated, warnings = validate_set(
            {"reps": 0, "weight": -50.0, "weight_unit": "kg", "rpe": 15}
        )
        assert len(warnings) == 3
        codes = {w.code for w in warnings}
        assert codes == {"invalid_reps", "negative_weight", "invalid_rpe"}


# ===================================================================
# validate_set — RIR + equipment_note
# ===================================================================


class TestValidateSetRirEquipment:
    def test_rir_only_converts_to_rpe(self):
        """RIR 2 with no RPE → RPE should be derived as 8.0."""
        validated, warnings = validate_set(
            {"reps": 5, "weight": 100.0, "weight_unit": "kg", "rir": 2}
        )
        assert validated.rir == 2
        assert validated.rpe == 8.0
        assert warnings == []

    def test_rir_half_point(self):
        """RIR 1.5 → RPE 8.5."""
        validated, warnings = validate_set({"reps": 5, "rir": 1.5})
        assert validated.rir == 1.5
        assert validated.rpe == 8.5
        assert warnings == []

    def test_rir_and_rpe_agree(self):
        """RIR 2 and RPE 8 agree — no warning."""
        validated, warnings = validate_set({"reps": 5, "rir": 2, "rpe": 8})
        assert validated.rir == 2
        assert validated.rpe == 8.0
        assert not any(w.code == "rir_rpe_conflict" for w in warnings)

    def test_rir_and_rpe_conflict(self):
        """RIR 2 implies RPE 8, but RPE 6 was given — warning + RIR wins."""
        validated, warnings = validate_set({"reps": 5, "rir": 2, "rpe": 6})
        assert validated.rir == 2
        assert validated.rpe == 8.0  # RIR-derived wins
        conflict_warnings = [w for w in warnings if w.code == "rir_rpe_conflict"]
        assert len(conflict_warnings) == 1
        assert "RIR 2" in conflict_warnings[0].message

    def test_rir_out_of_range_high(self):
        """RIR 12 → clamped to 10, with warning."""
        validated, warnings = validate_set({"reps": 5, "rir": 12})
        assert validated.rir == 10.0
        assert any(w.code == "invalid_rir" for w in warnings)

    def test_rir_negative(self):
        """RIR -1 → clamped to 0, with warning."""
        validated, warnings = validate_set({"reps": 5, "rir": -1})
        assert validated.rir == 0.0
        assert any(w.code == "invalid_rir" for w in warnings)

    def test_equipment_note_passthrough(self):
        validated, warnings = validate_set(
            {"reps": 10, "weight": 60.0, "weight_unit": "kg", "equipment_note": "with a red band"}
        )
        assert validated.equipment_note == "with a red band"
        assert warnings == []

    def test_equipment_note_default_none(self):
        validated, _ = validate_set({"reps": 10})
        assert validated.equipment_note is None

    def test_rir_default_none(self):
        validated, _ = validate_set({"reps": 10})
        assert validated.rir is None


# ===================================================================
# calculate_total_volume
# ===================================================================


class TestCalculateTotalVolume:
    def test_simple_volume(self):
        sets = (
            ValidatedSet(reps=10, weight_kg=80.0),
            ValidatedSet(reps=10, weight_kg=80.0),
            ValidatedSet(reps=8, weight_kg=85.0),
        )
        assert calculate_total_volume(sets) == 2280.0  # 800 + 800 + 680

    def test_no_sets(self):
        assert calculate_total_volume(None) is None

    def test_empty_sets(self):
        assert calculate_total_volume(()) is None

    def test_bodyweight_no_weight(self):
        sets = (
            ValidatedSet(reps=20),
            ValidatedSet(reps=15),
        )
        assert calculate_total_volume(sets) is None

    def test_mixed_weight_and_bodyweight(self):
        sets = (
            ValidatedSet(reps=10, weight_kg=80.0),
            ValidatedSet(reps=20),  # bodyweight set
        )
        assert calculate_total_volume(sets) == 800.0


# ===================================================================
# extract_pain_mentions
# ===================================================================


class TestExtractPainMentions:
    def test_no_pain_keywords(self):
        result = extract_pain_mentions("Great session today, really pushed hard")
        assert result == []

    def test_single_pain_mention(self):
        result = extract_pain_mentions("Client reported knee pain during squats")
        assert len(result) == 1
        assert result[0].body_part == "knee"
        assert result[0].severity_estimate == DEFAULT_SEVERITY

    def test_severity_modifier_mild(self):
        result = extract_pain_mentions("Mild lower back soreness after deadlifts")
        assert len(result) == 1
        assert result[0].body_part == "lower back"
        assert result[0].severity_estimate == 3  # "mild" → 3

    def test_severity_modifier_sharp(self):
        result = extract_pain_mentions("Sharp pain in left shoulder on overhead press")
        assert len(result) == 1
        assert result[0].body_part == "left shoulder"
        assert result[0].severity_estimate == 7  # "sharp" → 7

    def test_multiple_body_parts(self):
        result = extract_pain_mentions(
            "Knee soreness during squats. Also hip tightness on lunges"
        )
        assert len(result) == 2
        body_parts = {m.body_part for m in result}
        assert body_parts == {"knee", "hip"}

    def test_body_part_without_pain_keyword(self):
        result = extract_pain_mentions("Good knee stability on lunges")
        assert result == []

    def test_pain_without_body_part(self):
        result = extract_pain_mentions("Feeling sore from yesterday")
        assert result == []

    def test_case_insensitive(self):
        result = extract_pain_mentions("KNEE PAIN during squats")
        assert len(result) == 1
        assert result[0].body_part == "knee"

    def test_empty_string(self):
        assert extract_pain_mentions("") == []

    def test_whitespace_only(self):
        assert extract_pain_mentions("   ") == []

    def test_body_part_normalization_quads(self):
        result = extract_pain_mentions("Quads are sore from yesterday")
        assert len(result) == 1
        assert result[0].body_part == "quadriceps"

    def test_body_part_normalization_hammies(self):
        result = extract_pain_mentions("Hammies feel tight today")
        assert len(result) == 1
        assert result[0].body_part == "hamstring"

    def test_deduplication_same_body_part(self):
        result = extract_pain_mentions(
            "Mild knee pain on squats. Severe knee pain after lunges"
        )
        assert len(result) == 1
        assert result[0].body_part == "knee"
        assert result[0].severity_estimate == 8  # kept higher severity

    def test_lower_back_not_matched_as_back(self):
        result = extract_pain_mentions("Lower back pain after deadlifts")
        assert len(result) == 1
        assert result[0].body_part == "lower back"

    def test_multiple_sentences_mixed(self):
        result = extract_pain_mentions(
            "Great form on bench. Shoulder pain during overhead work. "
            "Ankles feel a bit tight"
        )
        assert len(result) == 2
        body_parts = {m.body_part for m in result}
        assert body_parts == {"shoulder", "ankle"}

    def test_pec_maps_to_chest(self):
        result = extract_pain_mentions("Pec strain on bench press")
        assert len(result) == 1
        assert result[0].body_part == "chest"

    # ---------------------------------------------------------------
    # Word boundary — no false positives on exercise language
    # ---------------------------------------------------------------

    def test_pulldown_no_false_positive(self):
        """'pull' should NOT match inside 'pulldown'."""
        result = extract_pain_mentions("Good form on back pulldowns")
        assert result == []

    def test_reached_no_false_positive(self):
        """'ache' should NOT match inside 'reached'."""
        result = extract_pain_mentions("Client reached a new PR on deadlift")
        assert result == []

    def test_standalone_pull_still_matches(self):
        result = extract_pain_mentions("Felt a pull in my hamstring")
        assert len(result) == 1
        assert result[0].body_part == "hamstring"

    # ---------------------------------------------------------------
    # Multi-word / new pain keywords
    # ---------------------------------------------------------------

    def test_gave_out_keyword(self):
        result = extract_pain_mentions("Knee gave out during lunges")
        assert len(result) == 1
        assert result[0].body_part == "knee"

    def test_locked_up_keyword(self):
        result = extract_pain_mentions("Back locked up on deadlifts")
        assert len(result) == 1
        assert result[0].body_part == "back"

    def test_flared_up_keyword(self):
        result = extract_pain_mentions("Shoulder flared up during press")
        assert len(result) == 1
        assert result[0].body_part == "shoulder"

    def test_tweaked_keyword(self):
        result = extract_pain_mentions("Tweaked my lower back on squat")
        assert len(result) == 1
        assert result[0].body_part == "lower back"

    def test_pop_keyword(self):
        result = extract_pain_mentions("Heard a pop in my knee")
        assert len(result) == 1
        assert result[0].body_part == "knee"

    def test_tear_keyword(self):
        result = extract_pain_mentions("Felt a tear in the calf")
        assert len(result) == 1
        assert result[0].body_part == "calf"

    # ---------------------------------------------------------------
    # New body parts
    # ---------------------------------------------------------------

    def test_traps_body_part(self):
        result = extract_pain_mentions("Traps are sore from shrugs")
        assert len(result) == 1
        assert result[0].body_part == "trapezius"

    def test_lats_body_part(self):
        result = extract_pain_mentions("Lats are tight after pulldowns")
        assert len(result) == 1
        assert result[0].body_part == "latissimus"

    def test_lat_not_inside_lateral(self):
        """'lat' should NOT match inside 'lateral'."""
        result = extract_pain_mentions("Good lateral movement today")
        assert result == []

    def test_it_band_body_part(self):
        result = extract_pain_mentions("IT band is tight on the right side")
        assert len(result) == 1
        assert result[0].body_part == "IT band"

    def test_hip_flexor_body_part(self):
        result = extract_pain_mentions("Hip flexor strain from lunges")
        assert len(result) == 1
        assert result[0].body_part == "hip flexor"

    def test_lumbar_body_part(self):
        result = extract_pain_mentions("Lumbar soreness after deadlifts")
        assert len(result) == 1
        assert result[0].body_part == "lumbar spine"

    def test_thoracic_body_part(self):
        result = extract_pain_mentions("Thoracic spine tightness today")
        assert len(result) == 1
        assert result[0].body_part == "thoracic spine"

    def test_oblique_body_part(self):
        result = extract_pain_mentions("Oblique strain from rotational work")
        assert len(result) == 1
        assert result[0].body_part == "oblique"

    def test_plantar_fascia_body_part(self):
        result = extract_pain_mentions("Plantar fascia pain in left foot")
        assert len(result) >= 1
        body_parts = {m.body_part for m in result}
        assert "plantar fascia" in body_parts

    def test_finger_body_part(self):
        result = extract_pain_mentions("Finger pain on grip exercises")
        assert len(result) == 1
        assert result[0].body_part == "finger"

    # ---------------------------------------------------------------
    # Negation handling
    # ---------------------------------------------------------------

    def test_no_knee_pain_negated(self):
        """'No knee pain today' should NOT create a pain mention."""
        result = extract_pain_mentions("No knee pain today")
        assert result == []

    def test_doesnt_hurt_negated(self):
        result = extract_pain_mentions("Shoulder doesn't hurt anymore")
        assert result == []

    def test_resolved_negated(self):
        result = extract_pain_mentions("Knee issue resolved now")
        assert result == []

    def test_negation_doesnt_affect_other_clauses(self):
        """Negation in one sentence shouldn't suppress pain in another."""
        result = extract_pain_mentions(
            "No knee pain today. But shoulder is sore"
        )
        assert len(result) == 1
        assert result[0].body_part == "shoulder"

    def test_real_pain_still_detected(self):
        result = extract_pain_mentions("Sharp knee pain on squats")
        assert len(result) == 1
        assert result[0].body_part == "knee"

    # ---------------------------------------------------------------
    # Comma splitting
    # ---------------------------------------------------------------

    def test_comma_separated_pain_mentions(self):
        """Two pain mentions separated by comma should both be detected."""
        result = extract_pain_mentions("Knee pain, shoulder tightness")
        assert len(result) == 2
        body_parts = {m.body_part for m in result}
        assert body_parts == {"knee", "shoulder"}

    def test_negation_plus_comma_interaction(self):
        """Negated clause + real pain clause after comma."""
        result = extract_pain_mentions(
            "No improvement, knee pain persists"
        )
        assert len(result) == 1
        assert result[0].body_part == "knee"

    # ---------------------------------------------------------------
    # New severity modifiers
    # ---------------------------------------------------------------

    def test_shooting_severity(self):
        result = extract_pain_mentions("Shooting pain down my leg")
        # "leg" is not a mapped body part, but "shooting" as a keyword
        # triggers pain detection. Let's test with a mapped body part.
        result = extract_pain_mentions("Shooting pain in my knee")
        assert len(result) == 1
        assert result[0].severity_estimate == 8

    def test_dull_severity(self):
        result = extract_pain_mentions("Dull ache in the shoulder")
        assert len(result) == 1
        assert result[0].severity_estimate == 3

    def test_nagging_severity(self):
        result = extract_pain_mentions("Nagging pain in the elbow")
        assert len(result) == 1
        assert result[0].severity_estimate == 4


# ===================================================================
# validate_set — suspicious value warnings
# ===================================================================


class TestValidateSetSuspiciousValues:
    def test_suspicious_reps_above_100(self):
        validated, warnings = validate_set({"reps": 200, "weight": 10.0, "weight_unit": "kg"})
        codes = {w.code for w in warnings}
        assert "suspicious_reps" in codes
        assert validated.reps == 200  # stored, not rejected

    def test_reps_100_no_warning(self):
        validated, warnings = validate_set({"reps": 100, "weight": 10.0, "weight_unit": "kg"})
        codes = {w.code for w in warnings}
        assert "suspicious_reps" not in codes

    def test_suspicious_weight_above_500kg(self):
        validated, warnings = validate_set({"reps": 5, "weight": 600.0, "weight_unit": "kg"})
        codes = {w.code for w in warnings}
        assert "suspicious_weight" in codes
        assert validated.weight_kg == 600.0  # stored, not rejected

    def test_weight_500kg_no_warning(self):
        validated, warnings = validate_set({"reps": 5, "weight": 500.0, "weight_unit": "kg"})
        codes = {w.code for w in warnings}
        assert "suspicious_weight" not in codes

    def test_suspicious_weight_lbs_conversion(self):
        """2000 lbs → ~907 kg → should warn."""
        validated, warnings = validate_set({"reps": 5, "weight": 2000.0, "weight_unit": "lbs"})
        codes = {w.code for w in warnings}
        assert "suspicious_weight" in codes


# ===================================================================
# validate_exercise_card
# ===================================================================


class TestValidateExerciseCard:
    def test_full_exercise_card(self, exercise_lookup):
        card = ParsedExerciseCard(
            exercise_name="bench press",
            sets=(
                ParsedSet(reps=10, weight=80.0, weight_unit="kg"),
                ParsedSet(reps=8, weight=85.0, weight_unit="kg", rpe=8),
            ),
            form_notes=("good depth",),
            cues_given=("drive through heels",),
        )
        result = validate_exercise_card(card, exercise_lookup)

        assert result.exercise_name == "bench press"
        assert result.exercise_match is not None
        assert result.exercise_match.canonical_name == "Barbell Bench Press"
        assert result.exercise_match.confidence == 100
        assert result.sets is not None
        assert len(result.sets) == 2
        assert result.sets[0].weight_kg == 80.0
        assert result.total_volume_kg == 1480.0  # 800 + 680
        assert result.form_notes == ("good depth",)
        assert result.cues_given == ("drive through heels",)

    def test_no_match_exercise(self):
        # Use a tiny lookup with only one entry to avoid WRatio false positives
        tiny_lookup = {"barbell bench press": "Barbell Bench Press"}
        card = ParsedExerciseCard(exercise_name="zzzxxx totally unknown")
        result = validate_exercise_card(card, tiny_lookup)

        assert result.exercise_match is None
        assert len(result.warnings) == 1
        assert result.warnings[0].code == "no_match"

    def test_lbs_conversion_in_card(self, exercise_lookup):
        card = ParsedExerciseCard(
            exercise_name="squat",
            sets=(ParsedSet(reps=5, weight=315.0, weight_unit="lbs"),),
        )
        result = validate_exercise_card(card, exercise_lookup)

        assert result.sets is not None
        assert result.sets[0].weight_kg == 142.9  # 315 * 0.453592
        assert result.sets[0].weight_original == 315.0
        assert result.sets[0].weight_unit_original == "lbs"

    def test_bodyweight_exercise(self, exercise_lookup):
        card = ParsedExerciseCard(
            exercise_name="pulldown",
            sets=(ParsedSet(reps=12), ParsedSet(reps=10)),
        )
        result = validate_exercise_card(card, exercise_lookup)

        assert result.total_volume_kg is None
        assert result.sets is not None
        assert len(result.sets) == 2

    def test_no_sets(self, exercise_lookup):
        card = ParsedExerciseCard(exercise_name="bench")
        result = validate_exercise_card(card, exercise_lookup)

        assert result.sets is None
        assert result.total_volume_kg is None


# ===================================================================
# validate_observation_card
# ===================================================================


class TestValidateObservationCard:
    def test_plain_observation(self):
        card = ParsedObservationCard(
            observation_text="Client arrived 10 minutes late"
        )
        result = validate_observation_card(card)

        assert result.observation_text == "Client arrived 10 minutes late"
        assert result.pain_mentions == ()
        assert result.flag_color is None

    def test_observation_with_pain(self):
        card = ParsedObservationCard(
            observation_text="Client reported mild knee pain during squats",
            flag_color="red",
            flag_reason="knee pain reported",
        )
        result = validate_observation_card(card)

        assert len(result.pain_mentions) == 1
        assert result.pain_mentions[0].body_part == "knee"
        assert result.flag_color == "red"
        assert result.flag_reason == "knee pain reported"

    def test_observation_with_flag_no_pain(self):
        card = ParsedObservationCard(
            observation_text="New personal record on deadlift",
            flag_color="green",
            flag_reason="new PR",
        )
        result = validate_observation_card(card)

        assert result.pain_mentions == ()
        assert result.flag_color == "green"

    def test_valid_attachment_both_fields(self):
        """Observation targeting entry [1], set 2 — passes validation."""
        card = ParsedObservationCard(
            observation_text="Left weaker than right on clamshells",
            target_entry_id=1,
            attached_to_set=2,
        )
        result = validate_observation_card(card, context_entry_count=3)

        assert result.target_entry_id == 1
        assert result.attached_to_set == 2
        assert result.warnings == ()

    def test_target_entry_id_out_of_range(self):
        """target_entry_id=5 but only 3 entries → cleared with warning."""
        card = ParsedObservationCard(
            observation_text="Form issue",
            target_entry_id=5,
            attached_to_set=1,
        )
        result = validate_observation_card(card, context_entry_count=3)

        assert result.target_entry_id is None
        assert result.attached_to_set is None
        assert len(result.warnings) == 1
        assert result.warnings[0].code == "invalid_target"

    def test_no_context_with_target(self):
        """target_entry_id set but context_entry_count=0 → cleared."""
        card = ParsedObservationCard(
            observation_text="Form looks off",
            target_entry_id=1,
            attached_to_set=1,
        )
        result = validate_observation_card(card, context_entry_count=0)

        assert result.target_entry_id is None
        assert result.attached_to_set is None
        assert len(result.warnings) == 1
        assert result.warnings[0].code == "no_context"

    def test_orphan_set_without_target(self):
        """attached_to_set=2 but no target_entry_id → cleared with warning."""
        card = ParsedObservationCard(
            observation_text="Something about set 2",
            attached_to_set=2,
        )
        result = validate_observation_card(card, context_entry_count=3)

        assert result.target_entry_id is None
        assert result.attached_to_set is None
        assert len(result.warnings) == 1
        assert result.warnings[0].code == "orphan_set"

    def test_invalid_set_number_below_one(self):
        """attached_to_set=0 → cleared with warning."""
        card = ParsedObservationCard(
            observation_text="Bad set reference",
            target_entry_id=1,
            attached_to_set=0,
        )
        result = validate_observation_card(card, context_entry_count=3)

        assert result.target_entry_id == 1
        assert result.attached_to_set is None
        assert len(result.warnings) == 1
        assert result.warnings[0].code == "invalid_set"

    def test_target_without_set_exercise_level(self):
        """target_entry_id set, attached_to_set omitted → exercise-level observation."""
        card = ParsedObservationCard(
            observation_text="Form breakdown on deadlift",
            target_entry_id=2,
        )
        result = validate_observation_card(card, context_entry_count=3)

        assert result.target_entry_id == 2
        assert result.attached_to_set is None
        assert result.warnings == ()

    def test_backward_compat_no_attachment_fields(self):
        """Observation with no attachment fields — same behavior as before."""
        card = ParsedObservationCard(
            observation_text="Client energy low",
            flag_color="yellow",
            flag_reason="fatigue",
        )
        result = validate_observation_card(card, context_entry_count=3)

        assert result.target_entry_id is None
        assert result.attached_to_set is None
        assert result.warnings == ()
        assert result.flag_color == "yellow"

    def test_negative_attached_to_set(self):
        """attached_to_set=-1 → cleared with warning (covered by < 1 check)."""
        card = ParsedObservationCard(
            observation_text="Bad set ref",
            target_entry_id=1,
            attached_to_set=-1,
        )
        result = validate_observation_card(card, context_entry_count=3)

        assert result.target_entry_id == 1
        assert result.attached_to_set is None
        assert len(result.warnings) == 1
        assert result.warnings[0].code == "invalid_set"

    def test_large_attached_to_set_accepted(self):
        """attached_to_set=100 with valid target — accepted (no upper bound check).

        By design: attached_to_set is a semantic hint, not validated against
        actual set count. Trainers may reference sets before they're logged.
        """
        card = ParsedObservationCard(
            observation_text="Something about set 100",
            target_entry_id=1,
            attached_to_set=100,
        )
        result = validate_observation_card(card, context_entry_count=3)

        assert result.target_entry_id == 1
        assert result.attached_to_set == 100
        assert result.warnings == ()


# ===================================================================
# validate_modification
# ===================================================================


class TestValidateModification:
    def test_valid_add_modification(self):
        mod = ParsedModification(
            target_entry_id=1,
            action="add",
            updates={"rpe": 8},
            form_notes=("good lockout",),
        )
        result, warnings = validate_modification(mod, context_entry_count=3)

        assert result.target_entry_id == 1
        assert result.action == "add"
        assert result.updates == {"rpe": 8}
        assert result.form_notes == ("good lockout",)
        assert warnings == []

    def test_valid_correct_modification(self):
        mod = ParsedModification(
            target_entry_id=2,
            action="correct",
            target_sets=(1, 2),
            updates={"weight": 85.0, "weight_unit": "kg"},
        )
        result, warnings = validate_modification(mod, context_entry_count=3)

        assert result.target_entry_id == 2
        assert result.action == "correct"
        assert result.target_sets == (1, 2)
        assert result.updates["weight_kg"] == 85.0
        assert warnings == []

    def test_target_out_of_range(self):
        mod = ParsedModification(target_entry_id=5, action="add")
        result, warnings = validate_modification(mod, context_entry_count=3)

        assert len(warnings) == 1
        assert warnings[0].code == "invalid_target"

    def test_target_zero(self):
        mod = ParsedModification(target_entry_id=0, action="add")
        _, warnings = validate_modification(mod, context_entry_count=3)

        assert len(warnings) == 1
        assert warnings[0].code == "invalid_target"

    def test_invalid_action(self):
        mod = ParsedModification(target_entry_id=1, action="delete")
        _, warnings = validate_modification(mod, context_entry_count=3)

        assert len(warnings) == 1
        assert warnings[0].code == "invalid_action"

    def test_weight_normalization_in_updates(self):
        mod = ParsedModification(
            target_entry_id=1,
            action="correct",
            updates={"weight": 185.0, "weight_unit": "lbs"},
        )
        result, _ = validate_modification(mod, context_entry_count=2)

        assert result.updates["weight_kg"] == 83.9
        assert result.updates["weight_original"] == 185.0
        assert result.updates["weight_unit_original"] == "lbs"

    def test_no_updates(self):
        mod = ParsedModification(
            target_entry_id=1,
            action="add",
            form_notes=("squeeze at top",),
        )
        result, warnings = validate_modification(mod, context_entry_count=2)

        assert result.updates is None
        assert result.form_notes == ("squeeze at top",)
        assert warnings == []

    def test_modification_rir_derives_rpe(self):
        """Modification with rir but no rpe → rpe derived from rir."""
        mod = ParsedModification(
            target_entry_id=1,
            action="add",
            updates={"rir": 2},
        )
        result, warnings = validate_modification(mod, context_entry_count=2)

        assert result.updates["rir"] == 2
        assert result.updates["rpe"] == 8.0
        assert warnings == []

    def test_modification_rir_rpe_conflict(self):
        """Modification with conflicting rir and rpe → rir wins + warning."""
        mod = ParsedModification(
            target_entry_id=1,
            action="add",
            updates={"rir": 2, "rpe": 6},
        )
        result, warnings = validate_modification(mod, context_entry_count=2)

        assert result.updates["rpe"] == 8.0  # RIR-derived wins
        conflict_warnings = [w for w in warnings if w.code == "rir_rpe_conflict"]
        assert len(conflict_warnings) == 1

    def test_modification_rir_rpe_agree(self):
        """Modification with agreeing rir and rpe → no warning."""
        mod = ParsedModification(
            target_entry_id=1,
            action="add",
            updates={"rir": 2, "rpe": 8},
        )
        result, warnings = validate_modification(mod, context_entry_count=2)

        assert result.updates["rpe"] == 8
        assert not any(w.code == "rir_rpe_conflict" for w in warnings)


# ===================================================================
# Adversarial edge cases — RIR boundaries, field combinations, coercion
# ===================================================================


class TestValidateSetBoundaries:
    def test_rir_boundary_zero_maximal_effort(self):
        """RIR=0 (maximal effort) → RPE=10.0, no warnings."""
        validated, warnings = validate_set({"reps": 1, "rir": 0})
        assert validated.rir == 0.0
        assert validated.rpe == 10.0
        assert warnings == []

    def test_rir_boundary_ten_minimal_effort(self):
        """RIR=10 → RPE=1.0 (clamped), warn for unusually high RIR."""
        validated, warnings = validate_set({"reps": 5, "rir": 10})
        assert validated.rir == 10.0
        assert validated.rpe == 1.0
        # RIR 10 is at the boundary — technically valid (clamped via convert_rir_to_rpe)
        assert not any(w.code == "invalid_rir" for w in warnings)

    def test_rir_fractional_0_5(self):
        """RIR=0.5 → RPE=9.5, half-point at the extreme end."""
        validated, warnings = validate_set({"reps": 3, "rir": 0.5})
        assert validated.rir == 0.5
        assert validated.rpe == 9.5
        assert warnings == []

    def test_equipment_note_survives_validation(self):
        """Equipment note + weight + reps all pass through validate_set together."""
        validated, warnings = validate_set({
            "reps": 10,
            "weight": 60.0,
            "weight_unit": "kg",
            "equipment_note": "red band over knees",
        })
        assert validated.equipment_note == "red band over knees"
        assert validated.weight_kg == 60.0
        assert validated.reps == 10
        assert warnings == []

    def test_all_new_fields_together(self):
        """Equipment_note + rir + lbs weight all at once — nothing interferes."""
        validated, warnings = validate_set({
            "reps": 8,
            "weight": 135.0,
            "weight_unit": "lbs",
            "rir": 3,
            "equipment_note": "with chains",
        })
        assert validated.rir == 3.0
        assert validated.rpe == 7.0  # RIR 3 → RPE 7
        assert validated.equipment_note == "with chains"
        assert validated.weight_kg == round(135.0 * 0.453592, 1)
        assert validated.weight_unit_original == "lbs"
        assert warnings == []

    def test_rir_string_coerced_to_number(self):
        """Claude sends rir: '2' (string) — coerced to float, not dropped."""
        validated, warnings = validate_set({"reps": 5, "rir": "2"})
        assert validated.rir == 2.0
        assert validated.rpe == 8.0
        assert warnings == []

    def test_rpe_string_coerced_to_number(self):
        """Claude sends rpe: '8' (string) — coerced to float, not dropped."""
        validated, warnings = validate_set({"reps": 5, "rpe": "8"})
        assert validated.rpe == 8.0
        assert warnings == []


class TestValidateModificationEdgeCases:
    def test_modification_equipment_note_passthrough(self):
        """validate_modification with equipment_note update — appears in output."""
        mod = ParsedModification(
            target_entry_id=1,
            action="add",
            target_sets=(3,),
            updates={"equipment_note": "with a red band"},
        )
        result, warnings = validate_modification(mod, context_entry_count=2)
        assert result.updates["equipment_note"] == "with a red band"
        assert not any(w.code == "invalid_target" for w in warnings)

    def test_modification_preserves_unmodified_fields(self):
        """Modify with {rpe: 8} only — weight/reps NOT present in normalized_updates."""
        mod = ParsedModification(
            target_entry_id=1,
            action="add",
            updates={"rpe": 8},
        )
        result, warnings = validate_modification(mod, context_entry_count=1)
        assert result.updates["rpe"] == 8
        assert "weight" not in result.updates
        assert "reps" not in result.updates
        assert "weight_kg" not in result.updates


# ===================================================================
# validate_parser_result (integration)
# ===================================================================


class TestValidateParserResult:
    def test_full_result_mixed_cards(self, exercise_lookup):
        parser_result = ParserResult(
            exercise_cards=(
                ParsedExerciseCard(
                    exercise_name="bench press",
                    sets=(ParsedSet(reps=10, weight=80.0, weight_unit="kg"),),
                ),
            ),
            observation_cards=(
                ParsedObservationCard(
                    observation_text="Client reported mild knee pain",
                    flag_color="red",
                    flag_reason="knee pain",
                ),
            ),
        )

        result = validate_parser_result(
            parser_result,
            exercise_lookup=exercise_lookup,
        )

        assert len(result.exercise_cards) == 1
        assert result.exercise_cards[0].exercise_match is not None
        assert result.exercise_cards[0].exercise_match.canonical_name == "Barbell Bench Press"

        assert len(result.observation_cards) == 1
        assert len(result.observation_cards[0].pain_mentions) == 1

    def test_result_with_modification(self, exercise_lookup):
        parser_result = ParserResult(
            exercise_cards=(),
            observation_cards=(),
            modifications=(
                ParsedModification(
                    target_entry_id=1,
                    action="add",
                    updates={"rpe": 8},
                ),
            ),
        )

        result = validate_parser_result(
            parser_result,
            exercise_lookup=exercise_lookup,
            context_entry_count=3,
        )

        assert len(result.modifications) == 1
        assert result.modifications[0].updates == {"rpe": 8}
        assert result.warnings == ()

    def test_warnings_aggregated(self):
        # Use tiny lookup so the exercise name triggers a no_match warning
        tiny_lookup = {"barbell bench press": "Barbell Bench Press"}
        parser_result = ParserResult(
            exercise_cards=(
                ParsedExerciseCard(
                    exercise_name="zzzxxx unknown",
                    sets=(ParsedSet(reps=-1),),
                ),
            ),
            observation_cards=(),
        )

        result = validate_parser_result(
            parser_result,
            exercise_lookup=tiny_lookup,
        )

        # Should have warnings: no match + invalid reps
        assert len(result.warnings) >= 2
        codes = {w.code for w in result.warnings}
        assert "no_match" in codes
        assert "invalid_reps" in codes

    def test_default_weight_unit_propagates(self, exercise_lookup):
        parser_result = ParserResult(
            exercise_cards=(
                ParsedExerciseCard(
                    exercise_name="bench",
                    sets=(ParsedSet(reps=5, weight=185.0),),
                ),
            ),
            observation_cards=(),
        )

        result = validate_parser_result(
            parser_result,
            default_weight_unit="lbs",
            exercise_lookup=exercise_lookup,
        )

        assert result.exercise_cards[0].sets[0].weight_kg == 83.9

    def test_empty_parser_result(self, exercise_lookup):
        parser_result = ParserResult(
            exercise_cards=(),
            observation_cards=(),
        )

        result = validate_parser_result(
            parser_result,
            exercise_lookup=exercise_lookup,
        )

        assert result.exercise_cards == ()
        assert result.observation_cards == ()
        assert result.modifications == ()
        assert result.warnings == ()

    def test_multiple_exercise_cards(self, exercise_lookup):
        parser_result = ParserResult(
            exercise_cards=(
                ParsedExerciseCard(
                    exercise_name="bench press",
                    sets=(ParsedSet(reps=10, weight=80.0, weight_unit="kg"),),
                ),
                ParsedExerciseCard(
                    exercise_name="squat",
                    sets=(ParsedSet(reps=5, weight=100.0, weight_unit="kg"),),
                ),
            ),
            observation_cards=(),
        )

        result = validate_parser_result(
            parser_result,
            exercise_lookup=exercise_lookup,
        )

        assert len(result.exercise_cards) == 2
        assert result.exercise_cards[0].exercise_match.canonical_name == "Barbell Bench Press"
        assert result.exercise_cards[1].exercise_match.canonical_name == "Barbell Back Squat"


# ===================================================================
# Full exercise DB spot-check (uses real 142-exercise DB)
# ===================================================================


class TestFullExerciseDB:
    @pytest.fixture
    def full_lookup(self) -> dict[str, str]:
        from app.services.transcription import load_exercise_db
        exercises = load_exercise_db()
        return build_exercise_lookup(exercises)

    def test_common_trainer_phrases(self, full_lookup):
        """Spot-check that common trainer phrases match correctly."""
        test_cases = [
            ("bench", "Barbell Bench Press"),
            ("squat", "Barbell Back Squat"),
            ("deadlift", "Conventional Deadlift"),
            ("RDL", "Romanian Deadlift"),
            ("lat pulldown", "Lat Pulldown"),
            ("leg press", "Leg Press"),
            ("bicep curl", "Barbell Curl"),
        ]
        for phrase, expected_canonical in test_cases:
            result = match_exercise_name(phrase, full_lookup)
            assert result is not None, f"No match for '{phrase}'"
            assert result.canonical_name == expected_canonical, (
                f"'{phrase}' matched '{result.canonical_name}', "
                f"expected '{expected_canonical}'"
            )

    def test_fuzzy_typos_against_full_db(self, full_lookup):
        """Common typos should still match."""
        result = match_exercise_name("benchh press", full_lookup)
        assert result is not None
        assert result.canonical_name == "Barbell Bench Press"

    def test_lookup_size(self, full_lookup):
        """Sanity check: full DB should have thousands of entries
        and every canonical name must be present as a lookup key."""
        assert len(full_lookup) > 3000

        from app.services.transcription import load_exercise_db
        exercises = load_exercise_db()
        canonical_names = {ex["canonical_name"] for ex in exercises}
        assert len(canonical_names) == 142

        # Every canonical name (lowercased) must appear as a key in the lookup
        lookup_keys = set(full_lookup.keys())
        missing = {name for name in canonical_names if name.lower() not in lookup_keys}
        assert missing == set(), f"Canonical names missing from lookup: {missing}"
