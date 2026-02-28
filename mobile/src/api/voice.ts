/**
 * Voice clip processing endpoint.
 *
 * Maps to backend route in api/voice.py:
 *   POST /api/v1/sessions/:sessionId/voice-clip → process audio
 *
 * Sends an audio file (m4a from expo-av) to the backend.
 * Backend pipeline: Deepgram STT → Claude parser → validation → persistence.
 * Returns structured entries + timing breakdown.
 */

import { apiPost, apiUpload } from "./client";
import type { DataResponse, VoiceClipResponse } from "./types";

/**
 * Upload a voice clip for processing.
 *
 * @param sessionId - The active session ID
 * @param audioUri - Local file URI from expo-av recording (file:///...)
 * @returns Processed entries, modifications, clarifications, and timing
 */
export async function processVoiceClip(
  sessionId: string,
  audioUri: string,
): Promise<VoiceClipResponse> {
  const formData = new FormData();

  // React Native's FormData accepts this shape for file uploads.
  // The 'as any' is standard RN pattern — FormData.append types
  // don't account for the { uri, type, name } convention.
  formData.append("audio", {
    uri: audioUri,
    type: "audio/mp4",
    name: "recording.m4a",
  } as any);

  const res = await apiUpload<DataResponse<VoiceClipResponse>>(
    `/api/v1/sessions/${sessionId}/voice-clip`,
    formData,
  );
  return res.data;
}

/**
 * Process typed text through the parser pipeline.
 *
 * Same output format as processVoiceClip — the text goes through
 * Claude parser → validation → persistence, skipping transcription.
 * Used when the trainer types an entry after a clarification prompt.
 */
export async function processTextEntry(
  sessionId: string,
  text: string,
): Promise<VoiceClipResponse> {
  const res = await apiPost<DataResponse<VoiceClipResponse>>(
    `/api/v1/sessions/${sessionId}/text-entry`,
    { text },
  );
  return res.data;
}

