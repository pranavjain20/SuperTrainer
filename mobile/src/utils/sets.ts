/**
 * Set data helpers for exercise cards.
 *
 * Handles both seed format ({ weight_kg, set }) and
 * voice pipeline format ({ weight, no explicit set number }).
 */

import type { SessionEntry, SetData, WeightUnit } from "@/src/api/types";

export function getSetWeight(set: SetData): string {
  const kg = set.weight ?? set.weight_kg;
  if (kg == null) return "—";
  return `${kg}kg`;
}

export function getSetNumber(set: SetData, index: number): number {
  return set.set ?? index + 1;
}

/**
 * Display reps or duration for timed exercises (planks, wall sits, etc.).
 * If duration_seconds is present, shows "60s" or "2m 30s".
 * Falls back to reps count.
 */
export function getSetReps(set: SetData): string {
  if (set.duration_seconds != null && set.duration_seconds > 0) {
    const sec = set.duration_seconds;
    if (sec >= 60) {
      const m = Math.floor(sec / 60);
      const s = sec % 60;
      return s > 0 ? `${m}m ${s}s` : `${m}m`;
    }
    return `${sec}s`;
  }
  return set.reps != null ? String(set.reps) : "—";
}

// ---------------------------------------------------------------------------
// Compact format helpers (collapsed session cards on client profile)
// ---------------------------------------------------------------------------

const KG_TO_LBS = 2.20462;

/** Convert weight from kg to the target unit, rounded to whole number. */
export function convertWeight(kg: number, unit: WeightUnit): number {
  if (unit === "lbs") return Math.round(kg * KG_TO_LBS);
  return Math.round(kg);
}

/**
 * Format a single set for compact display.
 *
 * Weighted:   "80kg×8"
 * Bodyweight: "12"
 * Timed:      "60s" / "2m 30s"
 */
export function formatCompactSet(set: SetData, unit: WeightUnit): string {
  // Timed exercises (plank, wall sit, etc.)
  if (set.duration_seconds != null && set.duration_seconds > 0) {
    return getSetReps(set);
  }

  const kg = set.weight ?? set.weight_kg;
  const reps = set.reps;

  // No weight — just reps
  if (kg == null || kg === 0) {
    return reps != null ? String(reps) : "—";
  }

  const w = convertWeight(kg, unit);
  const suffix = unit === "lbs" ? "lbs" : "kg";
  return reps != null ? `${w}${suffix}×${reps}` : `${w}${suffix}`;
}

/**
 * Format an exercise entry as a compact one-liner.
 *
 * "Squat: 80kg×8, 85kg×8, 90kg×6"
 * "Pull-ups: 12, 10, 8"
 * "Plank: 60s, 45s"
 */
function titleCase(s: string): string {
  return s.replace(/\b\w/g, (c) => c.toUpperCase());
}

export function formatCompactExercise(entry: SessionEntry, unit: WeightUnit): string {
  const raw = entry.exercise_name ?? entry.exercise_canonical ?? "Unknown";
  const name = titleCase(raw);
  if (!entry.sets || entry.sets.length === 0) return name;

  const parts = entry.sets.map((s) => formatCompactSet(s, unit));
  return `${name}: ${parts.join(", ")}`;
}

/**
 * Split version — returns name and sets separately for styled rendering.
 */
export function formatCompactExerciseParts(
  entry: SessionEntry,
  unit: WeightUnit,
): { name: string; sets: string } {
  const raw = entry.exercise_name ?? entry.exercise_canonical ?? "Unknown";
  const name = titleCase(raw);
  if (!entry.sets || entry.sets.length === 0) return { name, sets: "" };

  const parts = entry.sets.map((s) => formatCompactSet(s, unit));
  return { name, sets: parts.join(", ") };
}
