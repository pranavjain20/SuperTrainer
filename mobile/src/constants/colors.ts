/**
 * Legacy color file — kept for FLAG_COLORS and initialsColors which are
 * re-exported from tokens.ts. All other colors live in tokens.ts.
 *
 * Do not import this file directly. Import from "@/src/constants/tokens".
 */

/** Flag color map — shared by ObservationCard and edit modals. */
export const FLAG_COLORS: Record<string, string> = {
  green: "#22C55E",
  yellow: "#F59E0B",
  orange: "#F97316",
  red: "#EF4444",
};

/** Flag background colors — proper rgba alpha for dark backgrounds. */
export const FLAG_BG_COLORS: Record<string, string> = {
  green: "rgba(34, 197, 94, 0.12)",
  yellow: "rgba(245, 158, 11, 0.12)",
  orange: "rgba(249, 115, 22, 0.12)",
  red: "rgba(239, 68, 68, 0.12)",
};

/**
 * Deterministic color palette for client initials avatars.
 * Stable across the whole app (list + profile).
 */
export const initialsColors = [
  "#38BDF8", // sky blue
  "#8B5CF6", // violet
  "#EC4899", // pink
  "#F97316", // orange
  "#06B6D4", // cyan
  "#6366F1", // indigo
  "#22C55E", // emerald
  "#EAB308", // yellow
];
