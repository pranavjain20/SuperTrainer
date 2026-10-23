/**
 * The Brain — ask a question about your clients.
 *
 * Maps to backend route in api/brain.py:
 *   POST /api/v1/brain/ask → Claude answers from the trainer's training data
 */

import { apiPost } from "./client";
import type { BrainAnswer, DataResponse } from "./types";

export async function askBrain(question: string): Promise<string> {
  const res = await apiPost<DataResponse<BrainAnswer>>("/api/v1/brain/ask", { question });
  return res.data.answer;
}
