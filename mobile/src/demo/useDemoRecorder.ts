/**
 * The web demo's stand-in for useVoiceRecorder.
 *
 * Same interface and lifecycle (start → stop → URI), but instead of the
 * microphone it plays the next sample clip, so a visitor hears what the
 * trainer "said". The upload that follows is answered by server.ts with the
 * real pipeline's recorded result for that same clip.
 *
 * Like the real app, the trainer taps stop to send the clip.
 */

import { usePathname } from "expo-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { create } from "zustand";

import type { VoiceRecorder } from "@/src/hooks/useVoiceRecorder";
import { useRecordingStore } from "@/src/stores/recordingStore";

import fixture from "./fixture.json";
import { nextSessionClip } from "./server";

/** What the playing clip says, shown over the app by DemoFrame */
export const useDemoCaption = create<{ text: string | null; done: boolean }>(() => ({
  text: null,
  done: false,
}));

export function useDemoRecorder(): VoiceRecorder {
  const pathname = usePathname();
  const setGlobalRecording = useRecordingStore((s) => s.setIsRecording);
  const setGlobalStop = useRecordingStore((s) => s.setStopRecording);
  const [isRecording, setIsRecording] = useState(false);
  const [duration, setDuration] = useState(0);
  const [recordingUri, setRecordingUri] = useState<string | null>(null);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPlayback = useCallback(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    intervalRef.current = null;
    audioRef.current?.pause();
    audioRef.current = null;
    useDemoCaption.setState({ text: null, done: false });
  }, []);

  const startRecording = useCallback(async () => {
    if (audioRef.current) return;

    const sessionId = useRecordingStore.getState().activeSessionId;
    const clip =
      pathname.startsWith("/plans") || !sessionId
        ? { audio: fixture.plan_clip.audio, transcript: fixture.plan_clip.transcript }
        : (({ audio, response }) => ({ audio, transcript: response.transcript }))(
            nextSessionClip(sessionId),
          );

    const audio = new Audio(`/demo/${clip.audio}`);
    audio.onended = () => useDemoCaption.setState({ done: true });
    audioRef.current = audio;
    // Muted or blocked audio still shows the caption, so the demo works silently
    audio.play().catch(() => useDemoCaption.setState({ done: true }));

    useDemoCaption.setState({ text: clip.transcript, done: false });
    setIsRecording(true);
    setGlobalRecording(true);
    setDuration(0);
    setRecordingUri(null);

    const startedAt = Date.now();
    intervalRef.current = setInterval(() => {
      setDuration(Math.floor((Date.now() - startedAt) / 1000));
    }, 1000);
  }, [pathname, setGlobalRecording]);

  const stopRecording = useCallback(async (): Promise<string | null> => {
    if (!audioRef.current) return null;
    stopPlayback();
    setIsRecording(false);
    setGlobalRecording(false);
    // Unique per recording, like a real file URI: the session screen skips a repeated one
    const uri = `demo://sample-clip/${Date.now()}`;
    setRecordingUri(uri);
    return uri;
  }, [stopPlayback, setGlobalRecording]);

  const resetRecording = useCallback(() => {
    setRecordingUri(null);
    setDuration(0);
  }, []);

  useEffect(() => {
    setGlobalStop(stopRecording);
    return () => setGlobalStop(null);
  }, [stopRecording, setGlobalStop]);

  useEffect(() => {
    return () => {
      if (audioRef.current) setGlobalRecording(false);
      stopPlayback();
    };
  }, [stopPlayback, setGlobalRecording]);

  return {
    isRecording,
    duration,
    recordingUri,
    error: null,
    startRecording,
    stopRecording,
    resetRecording,
  };
}
