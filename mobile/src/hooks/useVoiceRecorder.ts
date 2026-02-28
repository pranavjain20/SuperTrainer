/**
 * Audio recording hook for voice clip capture.
 *
 * Manages the recording lifecycle: permission → record → stop → URI.
 * Produces m4a files (HIGH_QUALITY preset = 44kHz/128kbps AAC)
 * which match what voice.ts sends to the backend as audio/mp4.
 *
 * Day 6 will feed the recorded URI to processVoiceClip().
 */

import { Audio } from "expo-av";
import { useCallback, useEffect, useRef, useState } from "react";

import { useRecordingStore } from "@/src/stores/recordingStore";

interface VoiceRecorderState {
  isRecording: boolean;
  duration: number;
  recordingUri: string | null;
  error: string | null;
}

interface VoiceRecorderActions {
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<string | null>;
  resetRecording: () => void;
}

export type VoiceRecorder = VoiceRecorderState & VoiceRecorderActions;

export function useVoiceRecorder(): VoiceRecorder {
  const setGlobalRecording = useRecordingStore((s) => s.setIsRecording);
  const setGlobalStop = useRecordingStore((s) => s.setStopRecording);
  const [isRecording, setIsRecording] = useState(false);
  const [duration, setDuration] = useState(0);
  const [recordingUri, setRecordingUri] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const recordingRef = useRef<Audio.Recording | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number>(0);

  const clearDurationInterval = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const startRecording = useCallback(async () => {
    // If already recording, stop instead (toggle behavior)
    if (recordingRef.current) {
      return;
    }

    try {
      setError(null);

      // Request permission on first use
      const { granted } = await Audio.requestPermissionsAsync();
      if (!granted) {
        setError("Microphone permission is required to record sessions.");
        return;
      }

      // Configure audio mode for recording
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      // Create and start recording (HIGH_QUALITY = m4a at 44kHz/128kbps)
      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY,
      );

      recordingRef.current = recording;
      setIsRecording(true);
      setGlobalRecording(true);
      setDuration(0);
      setRecordingUri(null);

      // Track duration from wall clock to avoid drift
      startTimeRef.current = Date.now();
      intervalRef.current = setInterval(() => {
        setDuration(Math.floor((Date.now() - startTimeRef.current) / 1000));
      }, 1000);
    } catch (err) {
      setError("Failed to start recording. Please try again.");
      console.error("startRecording error:", err);
    }
  }, [setGlobalRecording]);

  const stopRecording = useCallback(async (): Promise<string | null> => {
    if (!recordingRef.current) return null;

    try {
      clearDurationInterval();

      await recordingRef.current.stopAndUnloadAsync();
      const uri = recordingRef.current.getURI();
      recordingRef.current = null;

      // Reset audio mode so playback works normally
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: false,
      });

      setIsRecording(false);
      setGlobalRecording(false);
      setRecordingUri(uri);
      return uri ?? null;
    } catch (err) {
      // Null out the ref even on error — a broken recording can't be reused,
      // and leaving it non-null blocks startRecording() from working.
      recordingRef.current = null;
      setIsRecording(false);
      setGlobalRecording(false);
      setError("Failed to stop recording.");
      console.error("stopRecording error:", err);
      return null;
    }
  }, [clearDurationInterval, setGlobalRecording]);

  const resetRecording = useCallback(() => {
    setRecordingUri(null);
    setError(null);
    setDuration(0);
  }, []);

  // Register stop function globally so tab layout can trigger it
  useEffect(() => {
    setGlobalStop(stopRecording);
    return () => setGlobalStop(null);
  }, [stopRecording, setGlobalStop]);

  // Cleanup on unmount: stop any active recording + clear interval
  useEffect(() => {
    return () => {
      clearDurationInterval();
      if (recordingRef.current) {
        recordingRef.current.stopAndUnloadAsync().catch(() => {});
        recordingRef.current = null;
        setGlobalRecording(false);
      }
    };
  }, [clearDurationInterval, setGlobalRecording]);

  return {
    isRecording,
    duration,
    recordingUri,
    error,
    startRecording,
    stopRecording,
    resetRecording,
  };
}
