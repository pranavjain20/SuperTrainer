/**
 * Session entries hook — fetches all entries for a session.
 *
 * Shares the cache key ["entries", "session", sessionId] with the
 * inline query in ExpandableSessionCard so both views stay in sync.
 *
 * staleTime is short (10s) because entries change frequently during
 * active recording — each voice clip creates new entries.
 */

import { useQuery } from "@tanstack/react-query";

import { getSessionEntries } from "@/src/api/entries";
import type { SessionEntry } from "@/src/api/types";

export function useSessionEntries(sessionId: string | undefined) {
  return useQuery({
    queryKey: ["entries", "session", sessionId],
    queryFn: async (): Promise<SessionEntry[]> => {
      const res = await getSessionEntries(sessionId!);
      return res.data;
    },
    enabled: !!sessionId,
    staleTime: 10_000,
  });
}
