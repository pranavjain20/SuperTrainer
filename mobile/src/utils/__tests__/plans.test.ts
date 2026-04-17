import type { PlannedExercise } from "@/src/api/types";
import { formatPlannedSets } from "../plans";

function ex(overrides: Partial<PlannedExercise> = {}): PlannedExercise {
  return { exercise_name: "Squats", sets: "", reps: "", weight: "", ...overrides };
}

describe("formatPlannedSets", () => {
  it("collapses uniform sets into 'N × weight×reps'", () => {
    expect(formatPlannedSets(ex({ sets: "4", reps: "8", weight: "10kg" })))
      .toBe("4 × 10kg×8");
  });

  it("shows single set as 'weight×reps' without count prefix", () => {
    expect(formatPlannedSets(ex({ sets: "1", reps: "8", weight: "60kg" })))
      .toBe("60kg×8");
  });

  it("expands per-set when weights vary", () => {
    expect(formatPlannedSets(ex({ sets: "3", reps: "8", weight: "10kg, 12kg, 14kg" })))
      .toBe("10kg×8, 12kg×8, 14kg×8");
  });

  it("expands per-set when reps vary", () => {
    expect(formatPlannedSets(ex({ sets: "3", reps: "12, 10, 8", weight: "60kg" })))
      .toBe("60kg×12, 60kg×10, 60kg×8");
  });

  it("trusts array length over sets field when they disagree", () => {
    // Parser sometimes emits sets=6 with 3 weights. Old code silently padded
    // with the first value, showing "12kg×12, 14kg×14, 16kg×16, 12kg×12,
    // 12kg×12, 12kg×12". Trust the declared weights instead.
    expect(formatPlannedSets(ex({
      sets: "6",
      reps: "12, 14, 16",
      weight: "12kg, 14kg, 16kg",
    }))).toBe("12kg×12, 14kg×14, 16kg×16");
  });

  it("handles weight-only (no reps) uniform case", () => {
    expect(formatPlannedSets(ex({ sets: "3", reps: "", weight: "20kg" })))
      .toBe("3 × 20kg");
  });

  it("handles reps-only (no weight) uniform case", () => {
    expect(formatPlannedSets(ex({ sets: "3", reps: "12", weight: "" })))
      .toBe("3 × 12");
  });

  it("returns empty string when all fields are blank", () => {
    expect(formatPlannedSets(ex())).toBe("");
  });

  it("handles varying weights with missing reps gracefully", () => {
    // weight array has 3 entries, reps is blank → still render 3 sets of weight alone
    expect(formatPlannedSets(ex({ sets: "3", reps: "", weight: "10kg, 12kg, 14kg" })))
      .toBe("10kg, 12kg, 14kg");
  });
});
