"""Classify a workout by its exercise composition.

Takes a list of exercise canonical names, looks up their primary muscles
from the exercise database, maps muscles to regions (push/pull/legs/core),
and derives a human-readable workout type label.
"""

from app.services.transcription import load_exercise_db

# ---------------------------------------------------------------------------
# Muscle → Region mapping
# ---------------------------------------------------------------------------
# Uses keyword matching against primary_muscles values from exercise_db.json.
# Order matters — first match wins, so more specific patterns come first.

_MUSCLE_REGION_RULES: list[tuple[str, str]] = [
    # Push muscles
    ("pectoralis", "push"),
    ("anterior deltoid", "push"),
    ("medial deltoid", "push"),
    ("triceps", "push"),
    ("serratus anterior", "push"),
    # Pull muscles
    ("latissimus", "pull"),
    ("rhomboid", "pull"),
    ("trapezius", "pull"),
    ("teres", "pull"),
    ("infraspinatus", "pull"),
    ("subscapularis", "pull"),
    ("posterior deltoid", "pull"),
    ("biceps brachii", "pull"),
    ("brachialis", "pull"),
    ("brachioradialis", "pull"),
    # Leg muscles
    ("quadriceps", "legs"),
    ("vastus", "legs"),
    ("rectus femoris", "legs"),
    ("gluteus", "legs"),
    ("gluteal", "legs"),
    ("biceps femoris", "legs"),
    ("hamstring", "legs"),
    ("semimembranosus", "legs"),
    ("semitendinosus", "legs"),
    ("gastrocnemius", "legs"),
    ("soleus", "legs"),
    ("tibialis", "legs"),
    ("adductor", "legs"),
    ("gracilis", "legs"),
    ("pectineus", "legs"),
    ("iliopsoas", "legs"),
    ("tensor fasciae", "legs"),
    ("piriformis", "legs"),
    ("gemellus", "legs"),
    ("obturator", "legs"),
    # Core muscles
    ("rectus abdominis", "core"),
    ("oblique", "core"),
    ("transversus abdominis", "core"),
    ("erector spinae", "core"),
    ("multifidus", "core"),
    ("quadratus lumborum", "core"),
]

# Region → human-readable label
_REGION_LABELS: dict[str, str] = {
    "push": "Upper Body Push",
    "pull": "Upper Body Pull",
    "legs": "Lower Body",
    "core": "Core",
    "conditioning": "Conditioning",
}

DOMINANCE_THRESHOLD = 0.70


def _classify_muscle(muscle_name: str) -> str | None:
    """Map a single muscle name to a region using keyword matching."""
    lower = muscle_name.lower()
    for keyword, region in _MUSCLE_REGION_RULES:
        if keyword in lower:
            return region
    return None


def classify_workout(exercise_canonical_names: list[str]) -> str:
    """Classify a workout from its exercise canonical names.

    Args:
        exercise_canonical_names: List of canonical exercise names from
            session entries (exercise_card only).

    Returns:
        Human-readable workout type label:
        - "Upper Body Push", "Upper Body Pull", "Lower Body", "Core"
        - "Upper Body" (mixed push + pull)
        - "Full Body" (multiple regions)
        - "Conditioning" (if category is conditioning)
        - "Session" (fallback for empty)
    """
    if not exercise_canonical_names:
        return "Session"

    exercises = load_exercise_db()
    exercise_map = {ex["canonical_name"].lower(): ex for ex in exercises}

    region_counts: dict[str, int] = {}
    total_classified = 0

    for name in exercise_canonical_names:
        ex = exercise_map.get(name.lower().replace("_", " "))
        if ex is None:
            continue

        # Conditioning category overrides muscle-based classification
        if ex.get("category") == "conditioning":
            region_counts["conditioning"] = region_counts.get("conditioning", 0) + 1
            total_classified += 1
            continue

        # Classify by primary muscles — find the dominant region for this exercise.
        # An exercise like Overhead Press has 3 push muscles + 1 pull muscle;
        # it should count as "push," not split across regions.
        muscle_region_tally: dict[str, int] = {}
        for muscle in ex.get("primary_muscles", []):
            region = _classify_muscle(muscle)
            if region:
                muscle_region_tally[region] = muscle_region_tally.get(region, 0) + 1

        if muscle_region_tally:
            dominant = max(muscle_region_tally, key=muscle_region_tally.get)  # type: ignore[arg-type]
            region_counts[dominant] = region_counts.get(dominant, 0) + 1
            total_classified += 1

    if total_classified == 0:
        return "Session"

    # Find dominant region
    sorted_regions = sorted(region_counts.items(), key=lambda x: x[1], reverse=True)
    top_region, top_count = sorted_regions[0]
    top_pct = top_count / total_classified

    if top_pct >= DOMINANCE_THRESHOLD:
        return _REGION_LABELS.get(top_region, "Session")

    # Mixed push + pull → "Upper Body" (only if they dominate together)
    push_count = region_counts.get("push", 0)
    pull_count = region_counts.get("pull", 0)
    if (push_count + pull_count) / total_classified >= DOMINANCE_THRESHOLD:
        if push_count > 0 and pull_count > 0:
            return "Upper Body"

    return "Full Body"
