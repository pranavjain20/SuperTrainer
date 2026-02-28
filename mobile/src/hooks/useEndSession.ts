/**
 * End-session orchestration hook.
 *
 * Two concerns:
 *   1. endSession — PATCH session with ended_at (server auto-computes duration)
 *   2. classifyWorkout — POST classify to get workout type label
 *
 * All mutations use TanStack Query. The classify query fires
 * automatically after ending (or on mount if session already ended).
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert } from "react-native";

import { classifyWorkout, updateSession } from "@/src/api/sessions";

interface UseEndSessionOptions {
  sessionId: string;
  isSessionEnded: boolean;
}

export function useEndSession({ sessionId, isSessionEnded }: UseEndSessionOptions) {
  const queryClient = useQueryClient();

  const endSessionMutation = useMutation({
    mutationFn: async () => {
      // Server auto-computes duration_minutes from ended_at - started_at
      return updateSession(sessionId, {
        ended_at: new Date().toISOString(),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
    },
    onError: (err) => {
      Alert.alert("Error", err instanceof Error ? err.message : "Failed to end session");
    },
  });

  // Classify workout — fires when session is ended
  const classifyQuery = useQuery({
    queryKey: ["sessions", sessionId, "classify"],
    queryFn: () => classifyWorkout(sessionId),
    enabled: isSessionEnded,
    staleTime: Infinity,
  });

  return {
    endSession: endSessionMutation.mutate,
    isEnding: endSessionMutation.isPending,
    workoutType: classifyQuery.data?.workout_type ?? null,
    isClassifying: classifyQuery.isLoading,
  };
}
