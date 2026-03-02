/**
 * Session data hooks.
 *
 * useTodaySessions() — today's sessions with client names attached.
 *
 * The backend returns sessions with client_id but no client name.
 * We fetch clients in parallel and join them client-side via useMemo.
 * TanStack Query caches the client list, so this join is essentially free
 * after the first load.
 */

import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";

import { getTrainerSessions } from "@/src/api/sessions";
import type { Client, Session } from "@/src/api/types";
import { useClientMap } from "./useClients";
import { toISODateString } from "@/src/utils/dates";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface SessionWithClient extends Session {
  client_name: string;
  client: Client | null;
}

// ---------------------------------------------------------------------------
// Query key factory
// ---------------------------------------------------------------------------

export const sessionsQueryKey = {
  all: ["sessions"] as const,
  byDate: (date: string) => ["sessions", "date", date] as const,
};

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Today's sessions enriched with client names.
 *
 * Fetches sessions and clients in parallel. Loading state is true
 * until BOTH resolve — prevents "Unknown Client" flicker.
 * Sessions sorted by scheduled_for/started_at time.
 */
export function useTodaySessions() {
  const today = toISODateString(new Date());

  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;

  const sessionsQuery = useQuery({
    queryKey: sessionsQueryKey.byDate(today),
    queryFn: async () => {
      const res = await getTrainerSessions({
        scheduled_for_date: today,
        tz,
        limit: 50,
      });
      return res.data;
    },
    staleTime: 60 * 1000, // 1 minute — sessions change more often
  });

  const clientMapQuery = useClientMap();

  // Join client names onto sessions once both queries have data.
  const sessions = useMemo<SessionWithClient[]>(() => {
    if (!sessionsQuery.data || !clientMapQuery.data) return [];

    return sessionsQuery.data
      .map((session) => {
        const client = clientMapQuery.data.get(session.client_id) ?? null;
        return {
          ...session,
          client_name: client?.name ?? "Unknown Client",
          client,
        };
      })
      .sort((a, b) => {
        const timeA = a.scheduled_for ?? a.started_at;
        const timeB = b.scheduled_for ?? b.started_at;
        return timeA.localeCompare(timeB);
      });
  }, [sessionsQuery.data, clientMapQuery.data]);

  return {
    data: sessions,
    isLoading: sessionsQuery.isLoading || clientMapQuery.isLoading,
    isError: sessionsQuery.isError || clientMapQuery.isError,
    error: sessionsQuery.error ?? clientMapQuery.error,
    refetch: async () => {
      await Promise.all([sessionsQuery.refetch(), clientMapQuery.refetch()]);
    },
  };
}
