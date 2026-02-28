/**
 * Client data hooks.
 *
 * useClients() — fetches all active clients, sorted alphabetically.
 * useClientMap() — same data as a Map<id, Client> for O(1) lookups.
 *
 * Both share the same TanStack Query cache — no duplicate fetches.
 */

import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";

import { getClients } from "@/src/api/clients";
import type { Client } from "@/src/api/types";

export const clientsQueryKey = ["clients"] as const;

/**
 * All active (non-archived) clients, sorted A-Z by name.
 *
 * limit: 200 covers any realistic trainer roster (15-40 clients).
 * staleTime: 5min — client list rarely changes mid-session.
 */
export function useClients() {
  return useQuery({
    queryKey: clientsQueryKey,
    queryFn: async () => {
      const res = await getClients({ limit: 200, include_archived: false });
      return res.data.sort((a, b) => a.name.localeCompare(b.name));
    },
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Client lookup map — resolves client_id → Client in O(1).
 *
 * Used by useTodaySessions to attach client names to sessions.
 * Reads from the same cache as useClients (no extra network request).
 */
export function useClientMap() {
  const query = useClients();

  const clientMap = useMemo(() => {
    const map = new Map<string, Client>();
    if (query.data) {
      for (const client of query.data) {
        map.set(client.id, client);
      }
    }
    return map;
  }, [query.data]);

  return { ...query, data: clientMap };
}
