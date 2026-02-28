/**
 * Set data helpers for exercise cards.
 *
 * Handles both seed format ({ weight_kg, set }) and
 * voice pipeline format ({ weight, no explicit set number }).
 */

import type { SetData } from "@/src/api/types";

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
