/**
 * Plan display utilities.
 *
 * formatPlannedSets — compact set string for a planned exercise, e.g.
 *   "4 × 10kg×8"                     (all sets identical)
 *   "10kg×8, 12kg×8, 14kg×8"         (varying weights, one rep scheme)
 *   "60kg×8"                          (single set)
 */

import type { PlannedExercise } from "@/src/api/types";

export function formatPlannedSets(ex: PlannedExercise): string {
  const numSets = parseInt(ex.sets || "", 10) || 0;
  const reps = (ex.reps || "").split(",").map((s) => s.trim()).filter(Boolean);
  const weights = (ex.weight || "").split(",").map((s) => s.trim()).filter(Boolean);

  const uniformReps = reps.length <= 1;
  const uniformWeight = weights.length <= 1;
  const uniform = uniformReps && uniformWeight;

  // Decide how many sets to actually render.
  // If weight/reps have multiple values, trust those arrays over `numSets`.
  // Prevents misleading silent padding when the parser emits e.g. sets=6
  // with only 3 weight values.
  const count = uniform
    ? Math.max(numSets, 1)
    : Math.max(reps.length, weights.length);

  const r0 = reps[0] ?? "";
  const w0 = weights[0] ?? "";

  // Uniform collapse: "4 × 10kg×8" beats "10kg×8, 10kg×8, 10kg×8, 10kg×8".
  if (uniform) {
    const pair = w0 && r0 ? `${w0}×${r0}` : r0 || w0;
    if (!pair) return "";
    return count > 1 ? `${count} × ${pair}` : pair;
  }

  // Per-set rendering: show each set's declared values. Reuse first value
  // when only one array is multi-valued (e.g. weights vary, reps held).
  const parts: string[] = [];
  for (let s = 0; s < count; s++) {
    const r = reps[s] ?? r0;
    const w = weights[s] ?? w0;
    if (w && r) parts.push(`${w}×${r}`);
    else if (r) parts.push(r);
    else if (w) parts.push(w);
  }
  return parts.join(", ");
}
