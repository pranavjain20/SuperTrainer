/**
 * Voice clip upload orchestration hook.
 *
 * Flow:
 *   1. startProcessing() → Zustand (shows spinner, disables record button)
 *   2. processVoiceClip(sessionId, audioUri) → backend API (~3s)
 *   3. invalidateQueries(["entries", "session", sessionId]) → TanStack refetch
 *   4. finishProcessing(clarifications) → Zustand
 *   5. On error: failProcessing(message, audioUri) → retry possible
 *
 * No optimistic updates — we can't predict what the backend returns
 * (canonical names, parsed structure, observation vs exercise split).
 */

import { useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";

import { processVoiceClip } from "@/src/api/voice";
import { useSessionStore } from "@/src/stores/sessionStore";

export function useVoiceClipUpload(sessionId: string) {
  const queryClient = useQueryClient();
  const { startProcessing, finishProcessing, failProcessing } = useSessionStore();

  const upload = useCallback(
    async (audioUri: string) => {
      startProcessing();

      try {
        const result = await processVoiceClip(sessionId, audioUri);

        // Refetch entries so new cards appear in the timeline
        await queryClient.invalidateQueries({
          queryKey: ["entries", "session", sessionId],
        });

        // Only surface clarifications when the parser produced nothing useful.
        // If entries were created or modified, the trainer sees the result and
        // can edit inline — no need for a confusing "didn't catch that" popup.
        const produced = result.entries_created.length + result.entries_modified.length;
        finishProcessing(produced > 0 ? [] : result.clarifications_needed);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to process voice clip";
        failProcessing(message, audioUri);
      }
    },
    [sessionId, queryClient, startProcessing, finishProcessing, failProcessing],
  );

  return { upload };
}
