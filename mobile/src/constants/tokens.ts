/**
 * Design system tokens — single source of truth.
 * Every color, font, spacing, and radius value comes from here.
 * No hardcoded hex values in component files.
 */

// Re-export legacy helpers so existing imports still work
export { FLAG_BG_COLORS, FLAG_COLORS, initialsColors } from "./colors";

export const colors = {
  // Backgrounds — depth stack (lighter = higher elevation)
  bg: {
    base: "#0F172A",
    surface1: "#1E293B",
    surface2: "#334155",
    surface3: "#475569",
  },

  // Text — never pure white, cap at #F1F5F9
  text: {
    primary: "#F1F5F9",
    secondary: "#94A3B8",
    tertiary: "#64748B",
    inverse: "#0F172A",
  },

  // Primary accent — sky blue
  blue: {
    500: "#38BDF8",
    600: "#0EA5E9",
    400: "#7DD3FC",
    900: "#0C4A6E",
    alpha12: "rgba(56, 189, 248, 0.12)",
  },

  // AI accent — purple (exclusively for AI-generated content)
  ai: {
    500: "#8B5CF6",
    400: "#A78BFA",
    900: "#1E1338",
    alpha10: "rgba(139, 92, 246, 0.10)",
  },

  // Semantic — status colors (desaturated for dark backgrounds)
  green: {
    500: "#22C55E",
    900: "#14332A",
    alpha12: "rgba(34, 197, 94, 0.12)",
  },
  amber: {
    500: "#F59E0B",
    900: "#332B14",
    alpha12: "rgba(245, 158, 11, 0.12)",
  },
  orange: {
    500: "#F97316",
    900: "#331E11",
    alpha12: "rgba(249, 115, 22, 0.12)",
  },
  red: {
    500: "#EF4444",
    900: "#331616",
    alpha12: "rgba(239, 68, 68, 0.12)",
  },

  // Recording state
  recording: {
    red: "#EF4444",
    glow: "rgba(239, 68, 68, 0.25)",
  },

  // Borders
  border: {
    subtle: "#475569",
    default: "#64748B",
    strong: "#94A3B8",
  },
} as const;

/**
 * Typography — 13-variant type scale.
 * Inter for text, JetBrains Mono for numeric data.
 */
export const typography = {
  display: {
    fontFamily: "Inter-Bold",
    fontSize: 34,
    lineHeight: 42,
  },
  "title-1": {
    fontFamily: "Inter-Bold",
    fontSize: 24,
    lineHeight: 30,
  },
  "title-2": {
    fontFamily: "Inter-SemiBold",
    fontSize: 20,
    lineHeight: 28,
  },
  "title-3": {
    fontFamily: "Inter-SemiBold",
    fontSize: 16,
    lineHeight: 22,
  },
  body: {
    fontFamily: "Inter-Regular",
    fontSize: 16,
    lineHeight: 24,
  },
  "body-medium": {
    fontFamily: "Inter-Medium",
    fontSize: 16,
    lineHeight: 24,
  },
  "body-small": {
    fontFamily: "Inter-Regular",
    fontSize: 14,
    lineHeight: 20,
  },
  caption: {
    fontFamily: "Inter-Medium",
    fontSize: 12,
    lineHeight: 16,
    letterSpacing: 0.8,
    textTransform: "uppercase" as const,
  },
  data: {
    fontFamily: "JetBrainsMono-Regular",
    fontSize: 16,
    lineHeight: 24,
  },
  "data-bold": {
    fontFamily: "JetBrainsMono-Bold",
    fontSize: 16,
    lineHeight: 24,
  },
  "data-large": {
    fontFamily: "JetBrainsMono-Bold",
    fontSize: 28,
    lineHeight: 34,
  },
  timer: {
    fontFamily: "JetBrainsMono-Regular",
    fontSize: 48,
    lineHeight: 56,
  },
  small: {
    fontFamily: "Inter-Regular",
    fontSize: 13,
    lineHeight: 18,
  },
} as const;

export type TypographyVariant = keyof typeof typography;

/** Spacing — 8px base grid with 4px sub-grid */
export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  base: 16,
  lg: 24,
  xl: 32,
  "2xl": 40,
  "3xl": 48,
} as const;

/** Border radii */
export const radii = {
  sm: 8,
  base: 12,
  lg: 16,
  pill: 24,
  full: 9999,
} as const;
