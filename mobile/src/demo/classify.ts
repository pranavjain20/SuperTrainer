/**
 * Workout classification for the demo, mirroring
 * backend/app/services/workout_classifier.py.
 *
 * The per-exercise half (muscles → region) is computed by the backend itself
 * and recorded in fixture.json as `exercise_regions`; only the counting below
 * is repeated here. classify.test.ts checks it against the backend's own
 * answers (`classifier_cases`).
 */

const REGION_LABELS: Record<string, string> = {
  push: "Upper Body Push",
  pull: "Upper Body Pull",
  legs: "Lower Body",
  core: "Core",
  conditioning: "Conditioning",
};

const DOMINANCE_THRESHOLD = 0.7;

export function classifyWorkout(
  canonicalNames: string[],
  exerciseRegions: Record<string, string>,
): string {
  if (canonicalNames.length === 0) return "Session";

  const regionByName = new Map(
    Object.entries(exerciseRegions).map(([name, region]) => [name.toLowerCase(), region]),
  );

  const regionCounts = new Map<string, number>();
  let totalClassified = 0;
  for (const name of canonicalNames) {
    const region = regionByName.get(name.toLowerCase().replace(/_/g, " "));
    if (!region) continue;
    regionCounts.set(region, (regionCounts.get(region) ?? 0) + 1);
    totalClassified += 1;
  }

  if (totalClassified === 0) return "Session";

  // Stable sort, like Python's sorted(): ties keep first-seen order
  const [topRegion, topCount] = [...regionCounts.entries()].sort(
    (a, b) => b[1] - a[1],
  )[0];
  if (topCount / totalClassified >= DOMINANCE_THRESHOLD) {
    return REGION_LABELS[topRegion] ?? "Session";
  }

  // Mixed push + pull → "Upper Body" (only if they dominate together)
  const push = regionCounts.get("push") ?? 0;
  const pull = regionCounts.get("pull") ?? 0;
  if ((push + pull) / totalClassified >= DOMINANCE_THRESHOLD && push > 0 && pull > 0) {
    return "Upper Body";
  }

  return "Full Body";
}
