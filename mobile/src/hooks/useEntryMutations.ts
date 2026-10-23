/**
 * Mutations for inline-editing and deleting session entries.
 *
 * Wraps the existing API functions with TanStack Query mutations.
 * Uses setQueryData for instant UI updates, plus invalidation for
 * background consistency.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { deleteEntry, updateEntry } from "@/src/api/entries";
import type { SessionEntry, SessionEntryUpdate } from "@/src/api/types";
import { summaryQueryKey } from "@/src/hooks/useEndSession";

export function useEntryMutations(sessionId: string) {
  const queryClient = useQueryClient();
  const queryKey = ["entries", "session", sessionId];

  // An edit changes the session's workout type, and the backend drops its
  // summary; refetch both (an open summary is rewritten for the edited session)
  const refreshSession = () => {
    queryClient.invalidateQueries({ queryKey: ["sessions"] });
    queryClient.invalidateQueries({ queryKey: summaryQueryKey(sessionId) });
  };

  const updateMutation = useMutation({
    mutationFn: ({ entryId, data }: { entryId: string; data: SessionEntryUpdate }) =>
      updateEntry(entryId, data),
    onSuccess: (updatedEntry) => {
      // Instantly patch the cached entry so cards re-render immediately
      queryClient.setQueryData<SessionEntry[]>(queryKey, (old) =>
        old?.map((e) => (e.id === updatedEntry.id ? updatedEntry : e)),
      );
      refreshSession();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (entryId: string) => deleteEntry(entryId),
    onSuccess: (_data, entryId) => {
      // Remove entry from cache immediately
      queryClient.setQueryData<SessionEntry[]>(queryKey, (old) =>
        old?.filter((e) => e.id !== entryId),
      );
      refreshSession();
    },
  });

  return { updateMutation, deleteMutation };
}
