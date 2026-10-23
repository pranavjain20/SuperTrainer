import fixture from "../fixture.json";
import { classifyWorkout } from "../classify";

// classifier_cases are the backend's own answers (workout_classifier.py),
// recorded by backend/scripts/export_web_demo.py.
describe("classifyWorkout matches the backend", () => {
  it.each(
    fixture.classifier_cases.map((c) => [c.names.join(", ") || "(none)", c] as const),
  )("%s", (_, { names, expected }) => {
    expect(classifyWorkout(names, fixture.exercise_regions)).toBe(expected);
  });

  it("covers every label the backend can return", () => {
    const labels = new Set(fixture.classifier_cases.map((c) => c.expected));
    expect([...labels].sort()).toEqual([
      "Conditioning",
      "Core",
      "Full Body",
      "Lower Body",
      "Session",
      "Upper Body",
      "Upper Body Pull",
      "Upper Body Push",
    ]);
  });

  it("matches names written with underscores or in another case", () => {
    expect(
      classifyWorkout(["goblet_squat", "ROMANIAN DEADLIFT"], fixture.exercise_regions),
    ).toBe("Lower Body");
  });
});
