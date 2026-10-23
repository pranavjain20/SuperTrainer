/**
 * End-session orchestration hook.
 *
 * Two concerns:
 *   1. endSession — PATCH session with ended_at (server auto-computes duration)
 *   2. summary — POST summary to get Claude's recap of the session
 *
 * The workout type comes on the session itself (session.workout_type).
 * The summary query fires automatically after ending (or on mount if the
 * session already ended). Its key sits outside ["sessions"] so refreshing
 * the session lists never re-triggers it.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert } from "react-native";

import { summarizeSession, updateSession } from "@/src/api/sessions";
import type { Session } from "@/src/api/types";

export const summaryQueryKey = (sessionId: string) => ["summary", sessionId] as const;

interface UseEndSessionOptions {
  sessionId: string;
  isSessionEnded: boolean;
}

export function useEndSession({ sessionId, isSessionEnded }: UseEndSessionOptions) {
  const queryClient = useQueryClient();

  const endSessionMutation = useMutation({
    mutationFn: async (endedAt: Date | void) => {
      // Server auto-computes duration_minutes from ended_at - started_at
      return updateSession(sessionId, {
        ended_at: (endedAt ?? new Date()).toISOString(),
      });
    },
    onSuccess: (updatedSession) => {
      // Immediately update the cached session so the UI transitions to ended state
      queryClient.setQueryData(["sessions", sessionId], updatedSession);
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
    },
    onError: (err) => {
      Alert.alert("Error", err instanceof Error ? err.message : "Failed to end session");
    },
  });

  // AI summary — fires when session is ended. Written once by the backend,
  // then stored; history cards read it from the session lists.
  const summaryQuery = useQuery({
    queryKey: summaryQueryKey(sessionId),
    queryFn: async () => {
      const aiSummary = await summarizeSession(sessionId);
      queryClient.setQueryData<Session>(["sessions", sessionId], (old) =>
        old ? { ...old, ai_summary: aiSummary } : old,
      );
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
      return aiSummary;
    },
    enabled: isSessionEnded,
    staleTime: Infinity,
    retry: 1,
  });

  return {
    endSession: endSessionMutation.mutate,
    isEnding: endSessionMutation.isPending,
    aiSummary: summaryQuery.data ?? null,
    isSummarizing: summaryQuery.isLoading,
  };
}
