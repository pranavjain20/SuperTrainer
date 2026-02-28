/**
 * Clean & minimal palette.
 * Apple Health / Linear aesthetic — light background, subtle colors, whitespace.
 */
export const colors = {
  // Backgrounds
  background: "#FAFAFA",
  surface: "#FFFFFF",
  surfaceSecondary: "#F5F5F5",

  // Text
  text: "#1A1A1A",
  textSecondary: "#6B7280",
  textTertiary: "#9CA3AF",

  // Brand
  primary: "#2563EB",
  primaryLight: "#DBEAFE",

  // Status
  success: "#10B981",
  warning: "#F59E0B",
  error: "#EF4444",

  // Flags (matching backend flag_color values)
  flagGreen: "#10B981",
  flagYellow: "#EAB308",
  flagOrange: "#F97316",
  flagRed: "#EF4444",

  // UI elements
  chevron: "#C8CCD0",
  observationDefault: "#6B7280",

  // Borders
  border: "#E5E7EB",
  borderLight: "#F3F4F6",

  // Tab bar
  tabActive: "#2563EB",
  tabInactive: "#9CA3AF",
} as const;

/** Flag color map — shared by ObservationCard and edit modals. */
export const FLAG_COLORS: Record<string, string> = {
  green: colors.flagGreen,
  yellow: colors.flagYellow,
  orange: colors.flagOrange,
  red: colors.flagRed,
};

/**
 * Deterministic color palette for client initials avatars.
 * Stable across the whole app (list + profile).
 */
export const initialsColors = [
  "#2563EB", // blue
  "#7C3AED", // violet
  "#DB2777", // pink
  "#EA580C", // orange
  "#0891B2", // cyan
  "#4F46E5", // indigo
  "#059669", // emerald
  "#CA8A04", // yellow
];
