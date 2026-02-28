/**
 * Single-client data hooks.
 *
 * useClient(id) — fetches one client by ID.
 * useClientSessions(id) — fetches that client's session history.
 * useClientPlans(id) — fetches that client's session plans.
 *
 * All are enabled only when id is truthy, so they're safe to call
 * before the route param is resolved.
 */

import { useQuery } from "@tanstack/react-query";

import { getClient } from "@/src/api/clients";
import { getClientPlans } from "@/src/api/plans";
import { getClientSessions } from "@/src/api/sessions";

export function useClient(id: string | undefined) {
  return useQuery({
    queryKey: ["clients", id],
    queryFn: () => getClient(id!),
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  });
}

export function useClientSessions(id: string | undefined) {
  return useQuery({
    queryKey: ["sessions", "client", id],
    queryFn: async () => {
      const res = await getClientSessions(id!, { limit: 20 });
      return res.data;
    },
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
}

export function useClientPlans(id: string | undefined) {
  return useQuery({
    queryKey: ["plans", "client", id],
    queryFn: async () => {
      const res = await getClientPlans(id!, { limit: 20 });
      return res.data;
    },
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  });
}
