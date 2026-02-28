/**
 * Session status display logic and derived stats.
 *
 * Shared between SessionRow (home/session list) and
 * SessionRecordingScreen (session detail header).
 */

import { colors } from "@/src/constants/colors";
import type { SessionEntry } from "@/src/api/types";

interface StatusDisplay {
  label: string;
  color: string;
}

interface SessionLike {
  ended_at: string | null;
  processing_status: string;
  scheduled_for: string | null;
}

export function getSessionDisplay(session: SessionLike): StatusDisplay {
  // Done
  if (session.ended_at) {
    return { label: "Done", color: colors.success };
  }

  // Actively processing audio
  if (session.processing_status === "processing") {
    return { label: "In Progress", color: colors.warning };
  }

  // No scheduled time — must be an ad-hoc session in progress
  if (!session.scheduled_for) {
    return { label: "In Progress", color: colors.warning };
  }

  const now = new Date();
  const scheduled = new Date(session.scheduled_for);
  const minutesUntil = Math.round(
    (scheduled.getTime() - now.getTime()) / 60000,
  );

  // Already past the scheduled time — in progress
  if (minutesUntil <= 0) {
    return { label: "In Progress", color: colors.warning };
  }

  // Under 1 hour away — show countdown
  if (minutesUntil < 60) {
    return { label: `In ${minutesUntil} min`, color: colors.warning };
  }

  // More than 1 hour away
  const hours = Math.floor(minutesUntil / 60);
  const remainingMin = minutesUntil % 60;
  const timeLabel =
    remainingMin > 0 ? `In ${hours}h ${remainingMin}m` : `In ${hours}h`;
  return { label: timeLabel, color: colors.textTertiary };
}

// ---------------------------------------------------------------------------
// Session stats (derived from entries in TanStack Query cache)
// ---------------------------------------------------------------------------

export interface SessionStats {
  exerciseCount: number;
  totalSets: number;
  totalVolumeKg: number;
  observationCount: number;
}

/**
 * Compute aggregate stats from a session's entries.
 *
 * Handles both set data formats produced by the backend:
 *   Seed data:      { weight_kg: 80, reps: 8 }
 *   Voice pipeline: { weight: 80, weight_unit: "kg", reps: 8 }
 */
export function computeSessionStats(entries: SessionEntry[]): SessionStats {
  let exerciseCount = 0;
  let totalSets = 0;
  let totalVolumeKg = 0;
  let observationCount = 0;

  for (const entry of entries) {
    if (entry.entry_type === "exercise_card") {
      exerciseCount++;
      if (entry.sets) {
        totalSets += entry.sets.length;
      }
      // Prefer pre-computed total_volume_kg when available
      if (entry.total_volume_kg != null) {
        totalVolumeKg += entry.total_volume_kg;
      }
    } else {
      observationCount++;
    }
  }

  return { exerciseCount, totalSets, totalVolumeKg, observationCount };
}

/**
 * Format the elapsed duration between two ISO timestamps.
 * Under 2 minutes → shows seconds ("45s", "90s").
 * Otherwise → "45m" or "1h 15m".
 */
export function formatSessionDuration(startedAt: string, endedAt: string): string {
  const start = new Date(startedAt).getTime();
  const end = new Date(endedAt).getTime();
  const totalSeconds = Math.max(0, Math.round((end - start) / 1000));

  if (totalSeconds < 120) return `${totalSeconds}s`;

  const totalMinutes = Math.round(totalSeconds / 60);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  if (hours === 0) return `${minutes}m`;
  if (minutes === 0) return `${hours}h`;
  return `${hours}h ${minutes}m`;
}

// ---------------------------------------------------------------------------
// Exercise numbering (DRY helper used by Timeline, recording, client profile)
// ---------------------------------------------------------------------------

/**
 * Assign sequential exercise numbers to exercise_card entries.
 *
 * Returns a Map of entryId → exerciseNumber. Observation cards are omitted.
 * Entries are numbered in sequence_order.
 */
export function numberExercises(entries: SessionEntry[]): Map<string, number> {
  const sorted = [...entries].sort((a, b) => a.sequence_order - b.sequence_order);
  const result = new Map<string, number>();
  let count = 0;
  for (const entry of sorted) {
    if (entry.entry_type === "exercise_card") {
      result.set(entry.id, ++count);
    }
  }
  return result;
}

/**
 * Format a duration_minutes integer for display.
 * 0 or 1 → "< 1m", otherwise "45m" / "1h 15m".
 */
export function formatDurationMinutes(minutes: number): string {
  if (minutes <= 1) return "< 1m";
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (hours === 0) return `${mins}m`;
  if (mins === 0) return `${hours}h`;
  return `${hours}h ${mins}m`;
}
