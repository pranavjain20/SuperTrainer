/**
 * Deterministic initials and color from a name.
 *
 * Used by ClientRow (list) and ClientDetailScreen (profile) —
 * same client always gets the same initials and color everywhere.
 */

import { initialsColors } from "@/src/constants/tokens";

export function getInitialsColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = hash + name.charCodeAt(i);
  }
  return initialsColors[hash % initialsColors.length];
}

export function getInitials(name: string): string {
  const trimmed = name.trim();
  if (!trimmed) return "?";
  const parts = trimmed.split(/\s+/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }
  return trimmed.slice(0, 2).toUpperCase();
}
