/**
 * Date formatting utilities for display throughout the app.
 *
 * All functions accept ISO 8601 strings (from the backend)
 * and return human-readable display strings.
 */

/**
 * "9:00 AM" — time only, for session cards.
 */
export function formatTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

/**
 * "Tuesday, February 25" — day header for home screen.
 */
export function formatDayHeader(date: Date): string {
  return date.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
}

/**
 * "Training since Mar 2025" — membership tenure for client profiles.
 */
export function formatMemberSince(isoDateString: string): string {
  const date = new Date(isoDateString);
  const month = date.toLocaleDateString("en-US", { month: "short" });
  return `Training since ${month} ${date.getFullYear()}`;
}

/**
 * "Mon, Feb 25" — short weekday + date for session list items.
 */
export function formatSessionDate(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

/**
 * "Feb 25, 2026" — date for session plans.
 *
 * planned_for_date is a calendar date ("2026-01-31"), not an instant.
 * Parsing it as-is defaults to UTC midnight, which in westward
 * timezones renders as the previous day. Append "T00:00:00" to
 * anchor it to local midnight.
 */
export function formatPlanDate(isoDate: string | null): string {
  if (!isoDate) return "No date";
  const date = new Date(isoDate + "T00:00:00");
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/**
 * "2026-02-25" — local date as ISO string for API queries.
 *
 * Uses local timezone (not UTC) so "today" matches the trainer's
 * actual day, not whatever UTC midnight is.
 */
export function toISODateString(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}
