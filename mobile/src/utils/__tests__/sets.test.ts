import type { SessionEntry, SetData, WeightUnit } from "@/src/api/types";
import { convertWeight, formatCompactExercise, formatCompactSet } from "../sets";
import { classifyWorkoutFromEntries } from "../sessions";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeSet(overrides: Partial<SetData> = {}): SetData {
  return { reps: null, rpe: null, ...overrides };
}

function makeEntry(overrides: Partial<SessionEntry> = {}): SessionEntry {
  return {
    id: "e1",
    session_id: "s1",
    client_id: "c1",
    entry_type: "exercise_card",
    sequence_order: 1,
    exercise_name: "Squat",
    exercise_canonical: null,
    sets: null,
    total_volume_kg: null,
    form_notes: null,
    cues_given: null,
    cue_effectiveness: null,
    observation_text: null,
    attached_to_set: null,
    flag_color: null,
    flag_reason: null,
    performed_at: null,
    created_at: "2025-01-01T00:00:00Z",
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// convertWeight
// ---------------------------------------------------------------------------

describe("convertWeight", () => {
  it("passes through kg unchanged", () => {
    expect(convertWeight(80, "kg")).toBe(80);
  });

  it("converts kg to lbs", () => {
    expect(convertWeight(100, "lbs")).toBe(220);
  });

  it("rounds to whole number", () => {
    // 80 * 2.20462 = 176.37
    expect(convertWeight(80, "lbs")).toBe(176);
  });

  it("rounds kg to whole number", () => {
    expect(convertWeight(82.5, "kg")).toBe(83);
  });
});

// ---------------------------------------------------------------------------
// formatCompactSet
// ---------------------------------------------------------------------------

describe("formatCompactSet", () => {
  it("formats a weighted set in kg", () => {
    const set = makeSet({ weight_kg: 80, reps: 8 });
    expect(formatCompactSet(set, "kg")).toBe("80kg×8");
  });

  it("formats a weighted set in lbs", () => {
    const set = makeSet({ weight: 100, reps: 5 });
    expect(formatCompactSet(set, "lbs")).toBe("220lbs×5");
  });

  it("formats a bodyweight set (no weight)", () => {
    const set = makeSet({ reps: 12 });
    expect(formatCompactSet(set, "kg")).toBe("12");
  });

  it("formats a bodyweight set (weight = 0)", () => {
    const set = makeSet({ weight: 0, reps: 10 });
    expect(formatCompactSet(set, "kg")).toBe("10");
  });

  it("formats a timed set", () => {
    const set = makeSet({ duration_seconds: 45 });
    expect(formatCompactSet(set, "kg")).toBe("45s");
  });

  it("formats a timed set at exactly 60s as minutes", () => {
    const set = makeSet({ duration_seconds: 60 });
    expect(formatCompactSet(set, "kg")).toBe("1m");
  });

  it("formats a long timed set", () => {
    const set = makeSet({ duration_seconds: 150 });
    expect(formatCompactSet(set, "kg")).toBe("2m 30s");
  });

  it("shows dash for missing data", () => {
    const set = makeSet({});
    expect(formatCompactSet(set, "kg")).toBe("—");
  });

  it("shows weight without reps when reps missing", () => {
    const set = makeSet({ weight_kg: 50 });
    expect(formatCompactSet(set, "kg")).toBe("50kg");
  });

  it("handles voice format (weight field)", () => {
    const set = makeSet({ weight: 60, reps: 10 });
    expect(formatCompactSet(set, "kg")).toBe("60kg×10");
  });
});

// ---------------------------------------------------------------------------
// formatCompactExercise
// ---------------------------------------------------------------------------

describe("formatCompactExercise", () => {
  it("formats an exercise with seed-format sets", () => {
    const entry = makeEntry({
      exercise_name: "Squat",
      sets: [
        makeSet({ weight_kg: 80, reps: 8 }),
        makeSet({ weight_kg: 85, reps: 8 }),
        makeSet({ weight_kg: 90, reps: 6 }),
      ],
    });
    expect(formatCompactExercise(entry, "kg")).toBe("Squat: 80kg×8, 85kg×8, 90kg×6");
  });

  it("formats an exercise with voice-format sets", () => {
    const entry = makeEntry({
      exercise_name: "Bench Press",
      sets: [
        makeSet({ weight: 60, reps: 10 }),
        makeSet({ weight: 60, reps: 8 }),
      ],
    });
    expect(formatCompactExercise(entry, "kg")).toBe("Bench Press: 60kg×10, 60kg×8");
  });

  it("formats a bodyweight exercise", () => {
    const entry = makeEntry({
      exercise_name: "Pull-ups",
      sets: [makeSet({ reps: 12 }), makeSet({ reps: 10 }), makeSet({ reps: 8 })],
    });
    expect(formatCompactExercise(entry, "kg")).toBe("Pull-Ups: 12, 10, 8");
  });

  it("formats a timed exercise", () => {
    const entry = makeEntry({
      exercise_name: "Plank",
      sets: [makeSet({ duration_seconds: 45 }), makeSet({ duration_seconds: 30 })],
    });
    expect(formatCompactExercise(entry, "kg")).toBe("Plank: 45s, 30s");
  });

  it("returns just the name when no sets", () => {
    const entry = makeEntry({ exercise_name: "Squat", sets: null });
    expect(formatCompactExercise(entry, "kg")).toBe("Squat");
  });

  it("returns just the name when sets array is empty", () => {
    const entry = makeEntry({ exercise_name: "Squat", sets: [] });
    expect(formatCompactExercise(entry, "kg")).toBe("Squat");
  });

  it("falls back to exercise_canonical when exercise_name is null", () => {
    const entry = makeEntry({
      exercise_name: null,
      exercise_canonical: "barbell_squat",
      sets: [makeSet({ weight_kg: 80, reps: 8 })],
    });
    expect(formatCompactExercise(entry, "kg")).toBe("Barbell_squat: 80kg×8");
  });

  it("shows Unknown when both names are null", () => {
    const entry = makeEntry({
      exercise_name: null,
      exercise_canonical: null,
      sets: [makeSet({ reps: 5 })],
    });
    expect(formatCompactExercise(entry, "kg")).toBe("Unknown: 5");
  });

  it("capitalizes lowercase exercise names", () => {
    const entry = makeEntry({
      exercise_name: "lat pull downs",
      sets: [makeSet({ weight_kg: 14, reps: 10 })],
    });
    expect(formatCompactExercise(entry, "kg")).toBe("Lat Pull Downs: 14kg×10");
  });

  it("formats in lbs when unit is lbs", () => {
    const entry = makeEntry({
      exercise_name: "Squat",
      sets: [makeSet({ weight_kg: 100, reps: 5 })],
    });
    expect(formatCompactExercise(entry, "lbs")).toBe("Squat: 220lbs×5");
  });
});

// ---------------------------------------------------------------------------
// classifyWorkoutFromEntries
// ---------------------------------------------------------------------------

describe("classifyWorkoutFromEntries", () => {
  it("classifies upper body workout", () => {
    const entries = [
      makeEntry({ exercise_name: "Bench Press" }),
      makeEntry({ exercise_name: "Pulldown" }),
      makeEntry({ exercise_name: "Bicep Curl" }),
    ];
    expect(classifyWorkoutFromEntries(entries)).toBe("Upper Body");
  });

  it("classifies lower body workout", () => {
    const entries = [
      makeEntry({ exercise_name: "Squat" }),
      makeEntry({ exercise_name: "Leg Press" }),
      makeEntry({ exercise_name: "Calf Raise" }),
    ];
    expect(classifyWorkoutFromEntries(entries)).toBe("Lower Body");
  });

  it("classifies full body workout", () => {
    const entries = [
      makeEntry({ exercise_name: "Squat" }),
      makeEntry({ exercise_name: "Bench Press" }),
      makeEntry({ exercise_name: "Deadlift" }),
    ];
    expect(classifyWorkoutFromEntries(entries)).toBe("Full Body");
  });

  it("classifies lat pull downs + squats + lunges as full body", () => {
    const entries = [
      makeEntry({ exercise_name: "lat pull downs" }),
      makeEntry({ exercise_name: "lunges" }),
      makeEntry({ exercise_name: "squats" }),
    ];
    expect(classifyWorkoutFromEntries(entries)).toBe("Full Body");
  });

  it("classifies core workout", () => {
    const entries = [
      makeEntry({ exercise_name: "Plank" }),
      makeEntry({ exercise_name: "Ab Crunch" }),
    ];
    expect(classifyWorkoutFromEntries(entries)).toBe("Core");
  });

  it("returns Workout for empty entries", () => {
    expect(classifyWorkoutFromEntries([])).toBe("Workout");
  });

  it("returns Workout when no keywords match", () => {
    const entries = [
      makeEntry({ exercise_name: "Kettlebell Swing" }),
      makeEntry({ exercise_name: "Box Jump" }),
    ];
    expect(classifyWorkoutFromEntries(entries)).toBe("Workout");
  });

  it("ignores observation cards", () => {
    const entries = [
      makeEntry({ exercise_name: "Bench Press", entry_type: "exercise_card" }),
      makeEntry({ exercise_name: null, entry_type: "observation_card", observation_text: "Good form" }),
    ];
    expect(classifyWorkoutFromEntries(entries)).toBe("Upper Body");
  });

  it("uses exercise_canonical as fallback", () => {
    const entries = [
      makeEntry({ exercise_name: null, exercise_canonical: "barbell_squat" }),
      makeEntry({ exercise_name: null, exercise_canonical: "leg_press" }),
    ];
    expect(classifyWorkoutFromEntries(entries)).toBe("Lower Body");
  });
});
