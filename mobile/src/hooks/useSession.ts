/**
 * Single-session data hook.
 *
 * useSession(id) — fetches one session by ID.
 * Enabled only when id is truthy, so it's safe to call
 * before the route param is resolved.
 */

import { useQuery } from "@tanstack/react-query";

import { getSession } from "@/src/api/sessions";

export function useSession(id: string | undefined) {
  return useQuery({
    queryKey: ["sessions", id],
    queryFn: () => getSession(id!),
    enabled: !!id,
    staleTime: 60 * 1000, // Sessions change often during recording
  });
}
