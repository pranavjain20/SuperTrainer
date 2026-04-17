"""Plan text parser service.

Takes natural language plan descriptions and uses Claude's tool_use
to extract structured exercise data. Handles freeform input like
"legs day, squats 4x8 at 60, RDLs 3x10" and produces exercises
with separate sets, reps, and weight fields for easy editing.
"""

from dataclasses import dataclass

import anthropic

from app.config import settings
from app.services.parser import DEFAULT_MODEL

# ---------------------------------------------------------------------------
# Tool schema
# ---------------------------------------------------------------------------

PLAN_PARSER_TOOL: dict = {
    "name": "record_workout_plan",
    "description": (
        "Record a structured workout plan from the trainer's natural language "
        "description. Extract the workout type and each exercise with its "
        "sets, reps, and weight as separate fields."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "workout_type": {
                "type": "string",
                "description": (
                    "A short name for the workout. If the trainer states it, "
                    "use their phrasing. Otherwise infer from the exercises: "
                    "all lower body → 'Legs', all upper body → 'Upper Body', "
                    "mix → 'Full Body', push exercises → 'Push', pull → 'Pull'. "
                    "Always provide a value — never omit. Always include "
                    "'Workout' or 'Session' in the name (e.g., 'Leg Workout', "
                    "'Upper Body Workout', not just 'Legs')."
                ),
            },
            "exercises": {
                "type": "array",
                "description": "List of exercises in the plan, in order.",
                "items": {
                    "type": "object",
                    "properties": {
                        "exercise_name": {
                            "type": "string",
                            "description": (
                                "The exercise name, cleaned up but recognizable. "
                                "Expand common abbreviations: 'RDL' → 'Romanian Deadlift', "
                                "'OHP' → 'Overhead Press', 'BB' → 'Barbell'. "
                                "Capitalize properly. Keep the trainer's intent — "
                                "if they say 'bench' it means 'Bench Press'."
                            ),
                        },
                        "sets": {
                            "type": "string",
                            "description": (
                                "Number of sets as a string. Usually a single number "
                                "like '4' or '3'. Use digits, not words. If not "
                                "mentioned, use an empty string."
                            ),
                        },
                        "reps": {
                            "type": "string",
                            "description": (
                                "Reps. If all sets have the same reps, write it "
                                "ONCE: '10' (not '10, 10, 10'). Only list multiple "
                                "values when reps vary between sets (pyramid): "
                                "'10, 8, 6'. For rep ranges: '8-12'. For timed: '30s'. "
                                "Use digits. If not mentioned, use empty string."
                            ),
                        },
                        "weight": {
                            "type": "string",
                            "description": (
                                "Weight. If all sets use the same weight, write it "
                                "ONCE: '20kg' (not '20kg, 20kg, 20kg'). Only list "
                                "multiple values when weight varies between sets: "
                                "'20kg, 22kg, 25kg'. Include the unit. If bodyweight "
                                "or not mentioned, use an empty string."
                            ),
                        },
                    },
                    "required": ["exercise_name", "sets", "reps", "weight"],
                },
            },
        },
        "required": ["workout_type", "exercises"],
    },
}

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

PLAN_PARSER_SYSTEM_PROMPT: str = """\
You are a workout plan parser. A personal trainer has described an upcoming \
workout plan in natural language. Your job is to extract the structured plan \
by calling the record_workout_plan tool.

Rules:
1. Extract every distinct exercise mentioned. Preserve the order.
2. Expand abbreviations to readable names: RDL → Romanian Deadlift, \
OHP → Overhead Press, BB → Barbell, DB → Dumbbell, KB → Kettlebell.
3. Extract sets, reps, and weight as SEPARATE fields. \
"four sets of eight at sixty kilos" → sets="4", reps="8", weight="60kg". \
"3 sets of 10, 8, 6 at 20, 22, 25 kg" → sets="3", reps="10, 8, 6", \
weight="20kg, 22kg, 25kg".
4. If the trainer says something like "4 sets each" for multiple exercises, \
apply sets="4" to each exercise.
5. If an exercise has no specific sets/reps/weight, use empty strings.
6. ALWAYS set workout_type as a workout NAME (not just a body part). If the \
trainer states it, use their phrasing. If not stated, infer from exercises: \
all lower body → "Leg Workout", all upper body → "Upper Body Workout", \
mix → "Full Body Workout", push → "Push Workout", pull → "Pull Workout", \
cardio/stretching → "Recovery Session". Always append "Workout" or "Session" \
to make it a name, not just a label.
7. Ignore non-exercise content (greetings, filler words).
8. Always use digits, never words for numbers.
9. Never leave trailing commas in any field. "10kg, 12kg" not "10kg, 12kg,".
"""


# ---------------------------------------------------------------------------
# Parser function
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PlannedExercise:
    exercise_name: str
    sets: str
    reps: str
    weight: str


@dataclass(frozen=True)
class PlanParseResult:
    workout_type: str | None
    exercises: list[PlannedExercise]


async def parse_plan_text(text: str) -> PlanParseResult:
    """Parse natural language plan text into structured exercises.

    Args:
        text: Free-form plan description from the trainer.

    Returns:
        PlanParseResult with workout_type and list of exercises.
    """
    if not text.strip():
        raise ValueError("Plan text must not be empty")

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    response = await client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=1024,
        system=PLAN_PARSER_SYSTEM_PROMPT,
        tools=[PLAN_PARSER_TOOL],
        tool_choice={"type": "tool", "name": "record_workout_plan"},
        messages=[
            {"role": "user", "content": text},
        ],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "record_workout_plan":
            data = block.input
            exercises = [
                PlannedExercise(
                    exercise_name=ex["exercise_name"],
                    sets=ex.get("sets", ""),
                    reps=ex.get("reps", ""),
                    weight=ex.get("weight", ""),
                )
                for ex in data.get("exercises", [])
            ]
            return PlanParseResult(
                workout_type=data.get("workout_type"),
                exercises=exercises,
            )

    return PlanParseResult(workout_type=None, exercises=[])
