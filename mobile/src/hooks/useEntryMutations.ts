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

export function useEntryMutations(sessionId: string) {
  const queryClient = useQueryClient();
  const queryKey = ["entries", "session", sessionId];

  const updateMutation = useMutation({
    mutationFn: ({ entryId, data }: { entryId: string; data: SessionEntryUpdate }) =>
      updateEntry(entryId, data),
    onSuccess: (updatedEntry) => {
      // Instantly patch the cached entry so cards re-render immediately
      queryClient.setQueryData<SessionEntry[]>(queryKey, (old) =>
        old?.map((e) => (e.id === updatedEntry.id ? updatedEntry : e)),
      );
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (entryId: string) => deleteEntry(entryId),
    onSuccess: (_data, entryId) => {
      // Remove entry from cache immediately
      queryClient.setQueryData<SessionEntry[]>(queryKey, (old) =>
        old?.filter((e) => e.id !== entryId),
      );
    },
  });

  return { updateMutation, deleteMutation };
}
