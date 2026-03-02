/**
 * Shared style objects used across multiple components.
 */

import { colors } from "./tokens";

/** Card border — replaces cardShadow for dark theme. Depth from borders, not shadows. */
export const cardBorder = {
  borderWidth: 1,
  borderColor: colors.border.subtle,
} as const;

/** @deprecated Use cardBorder instead. Kept for backwards compat during migration. */
export const cardShadow = cardBorder;
