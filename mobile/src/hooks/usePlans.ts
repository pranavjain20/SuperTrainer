/**
 * Plan mutation hooks.
 *
 * Cache updates use setQueryData with the server response rather than
 * refetchQueries. Two reasons:
 *   1. Instant UI update — no waiting for a round-trip GET.
 *   2. Survives navigation boundaries. refetchQueries defaults to matching
 *      only active observers, which is fragile when the mutation fires
 *      from a pushed screen whose parent may be detached in the stack.
 *
 * invalidateQueries runs as a backstop so any other cached variants of
 * this client's plans list get refreshed the next time they're observed.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Alert } from "react-native";

import { createPlan, deletePlan, parsePlanText, updatePlan } from "@/src/api/plans";
import type { SessionPlan, SessionPlanCreate, SessionPlanUpdate } from "@/src/api/types";

function plansKey(clientId: string) {
  return ["plans", "client", clientId] as const;
}

export function useCreatePlan(clientId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: SessionPlanCreate) => createPlan(data),
    onSuccess: (newPlan) => {
      queryClient.setQueryData<SessionPlan[]>(plansKey(clientId), (prev) =>
        prev ? [newPlan, ...prev] : [newPlan],
      );
      queryClient.invalidateQueries({ queryKey: plansKey(clientId) });
    },
    onError: (err) => {
      Alert.alert("Error", err instanceof Error ? err.message : "Failed to create plan");
    },
  });
}

export function useUpdatePlan(clientId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ planId, data }: { planId: string; data: SessionPlanUpdate }) =>
      updatePlan(planId, data),
    onSuccess: (updated) => {
      queryClient.setQueryData<SessionPlan[]>(plansKey(clientId), (prev) =>
        prev ? prev.map((p) => (p.id === updated.id ? updated : p)) : [updated],
      );
      queryClient.invalidateQueries({ queryKey: plansKey(clientId) });
    },
    onError: (err) => {
      Alert.alert("Error", err instanceof Error ? err.message : "Failed to update plan");
    },
  });
}

export function useDeletePlan(clientId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (planId: string) => deletePlan(planId),
    onSuccess: (_, planId) => {
      queryClient.setQueryData<SessionPlan[]>(plansKey(clientId), (prev) =>
        prev ? prev.filter((p) => p.id !== planId) : prev,
      );
      queryClient.invalidateQueries({ queryKey: plansKey(clientId) });
    },
    onError: (err) => {
      Alert.alert("Error", err instanceof Error ? err.message : "Failed to delete plan");
    },
  });
}

export function useParsePlan() {
  return useMutation({
    mutationFn: (text: string) => parsePlanText(text),
    onError: (err) => {
      Alert.alert("Error", err instanceof Error ? err.message : "Failed to parse plan");
    },
  });
}
