/**
 * Plan mutation hooks.
 *
 * useCreatePlan — POST new plan, refetches client plans list.
 * useUpdatePlan — PATCH existing plan, refetches client plans list.
 * useDeletePlan — DELETE plan, refetches client plans list.
 * useParsePlan — Parse natural language into structured exercises.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Alert } from "react-native";

import { createPlan, deletePlan, parsePlanText, updatePlan } from "@/src/api/plans";
import type { SessionPlanCreate, SessionPlanUpdate } from "@/src/api/types";

export function useCreatePlan(clientId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: SessionPlanCreate) => createPlan(data),
    onSuccess: async () => {
      await queryClient.refetchQueries({ queryKey: ["plans", "client", clientId] });
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
    onSuccess: async () => {
      await queryClient.refetchQueries({ queryKey: ["plans", "client", clientId] });
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
    onSuccess: async () => {
      await queryClient.refetchQueries({ queryKey: ["plans", "client", clientId] });
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
