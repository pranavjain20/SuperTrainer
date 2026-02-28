/**
 * Global recording state — shared between useVoiceRecorder and tab layout.
 *
 * The tab layout needs to know if a recording is active so it can
 * warn the trainer before navigating away. The recorder hook syncs
 * this store whenever recording starts or stops.
 *
 * stopRecording is set by useVoiceRecorder on mount — it points to the
 * hook's stopRecording function so the tab layout can trigger a stop
 * without importing expo-av directly.
 */

import { create } from "zustand";

interface RecordingStore {
  isRecording: boolean;
  setIsRecording: (value: boolean) => void;
  stopRecording: (() => Promise<string | null>) | null;
  setStopRecording: (fn: (() => Promise<string | null>) | null) => void;

  // Active session metadata — persists even when not recording a clip
  activeSessionId: string | null;
  activeClientName: string | null;
  activeSessionStartedAt: string | null;
  setActiveSession: (id: string, clientName: string, startedAt: string) => void;
  clearActiveSession: () => void;
}

export const useRecordingStore = create<RecordingStore>((set) => ({
  isRecording: false,
  setIsRecording: (value) => set({ isRecording: value }),
  stopRecording: null,
  setStopRecording: (fn) => set({ stopRecording: fn }),

  activeSessionId: null,
  activeClientName: null,
  activeSessionStartedAt: null,
  setActiveSession: (id, clientName, startedAt) =>
    set({ activeSessionId: id, activeClientName: clientName, activeSessionStartedAt: startedAt }),
  clearActiveSession: () =>
    set({ activeSessionId: null, activeClientName: null, activeSessionStartedAt: null }),
}));
