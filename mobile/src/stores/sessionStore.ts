/**
 * Ephemeral session recording state.
 *
 * Tracks voice clip processing lifecycle (uploading, errors, retries)
 * and accumulates clarifications from the AI parser across clips.
 *
 * This state doesn't belong in TanStack Query — it's UI-only and
 * resets when the trainer leaves the recording screen.
 */

import { create } from "zustand";

import type { ClarificationItem } from "@/src/api/types";

interface SessionStoreState {
  isProcessing: boolean;
  processingError: string | null;
  failedAudioUri: string | null;
  clarifications: ClarificationItem[];
}

interface SessionStoreActions {
  startProcessing: () => void;
  finishProcessing: (clarifications: ClarificationItem[]) => void;
  failProcessing: (error: string, audioUri: string) => void;
  clearError: () => void;
  dismissClarification: (index: number) => void;
  clearClarifications: () => void;
  reset: () => void;
}

type SessionStore = SessionStoreState & SessionStoreActions;

const initialState: SessionStoreState = {
  isProcessing: false,
  processingError: null,
  failedAudioUri: null,
  clarifications: [],
};

export const useSessionStore = create<SessionStore>((set) => ({
  ...initialState,

  startProcessing: () =>
    set({ isProcessing: true, processingError: null, failedAudioUri: null }),

  finishProcessing: (clarifications) =>
    set({
      isProcessing: false,
      // Each clip result fully replaces previous state — useVoiceClipUpload
      // passes [] when entries are produced, clearing stale clarifications.
      clarifications,
    }),

  failProcessing: (error, audioUri) =>
    set({ isProcessing: false, processingError: error, failedAudioUri: audioUri }),

  clearError: () =>
    set({ processingError: null, failedAudioUri: null }),

  dismissClarification: (index) =>
    set((state) => ({
      clarifications: state.clarifications.filter((_, i) => i !== index),
    })),

  clearClarifications: () => set({ clarifications: [] }),

  reset: () => set(initialState),
}));
