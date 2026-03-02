/**
 * Session API endpoints.
 *
 * Backend routes (sessions router has prefix="/sessions"):
 *   GET    /api/v1/sessions                          → trainer-level list (date filter)
 *   POST   /api/v1/sessions                          → create
 *   GET    /api/v1/sessions/:id                      → get
 *   PATCH  /api/v1/sessions/:id                      → update
 *   DELETE /api/v1/sessions/:id                      → delete
 *
 * Client-scoped list lives in the clients router:
 *   GET    /api/v1/clients/:clientId/sessions         → list by client
 */

import { apiDelete, apiGet, apiPatch, apiPost } from "./client";
import type {
  DataResponse,
  ListResponse,
  Session,
  SessionCreate,
  SessionUpdate,
  WorkoutClassification,
} from "./types";

// ---------------------------------------------------------------------------
// Trainer-level list (home screen — "all my sessions today")
// ---------------------------------------------------------------------------

interface TrainerSessionParams {
  scheduled_for_date?: string; // ISO date, e.g. "2026-02-25"
  tz?: string;                 // IANA timezone, e.g. "America/New_York"
  cursor?: string;
  limit?: number;
}

export async function getTrainerSessions(
  params?: TrainerSessionParams,
): Promise<ListResponse<Session>> {
  return apiGet<ListResponse<Session>>("/api/v1/sessions", params);
}

// ---------------------------------------------------------------------------
// Client-scoped list (client profile — session history)
// ---------------------------------------------------------------------------

interface ClientSessionParams {
  cursor?: string;
  limit?: number;
}

export async function getClientSessions(
  clientId: string,
  params?: ClientSessionParams,
): Promise<ListResponse<Session>> {
  return apiGet<ListResponse<Session>>(`/api/v1/clients/${clientId}/sessions`, params);
}

// ---------------------------------------------------------------------------
// Single resource
// ---------------------------------------------------------------------------

export async function getSession(sessionId: string): Promise<Session> {
  const res = await apiGet<DataResponse<Session>>(`/api/v1/sessions/${sessionId}`);
  return res.data;
}

// ---------------------------------------------------------------------------
// Create
// ---------------------------------------------------------------------------

export async function createSession(data: SessionCreate): Promise<Session> {
  const res = await apiPost<DataResponse<Session>>("/api/v1/sessions", data);
  return res.data;
}

// ---------------------------------------------------------------------------
// Update (e.g., ending a session)
// ---------------------------------------------------------------------------

export async function updateSession(
  sessionId: string,
  data: SessionUpdate,
): Promise<Session> {
  const res = await apiPatch<DataResponse<Session>>(
    `/api/v1/sessions/${sessionId}`,
    data,
  );
  return res.data;
}

// ---------------------------------------------------------------------------
// Classify workout
// ---------------------------------------------------------------------------

export async function classifyWorkout(
  sessionId: string,
): Promise<WorkoutClassification> {
  const res = await apiPost<DataResponse<WorkoutClassification>>(
    `/api/v1/sessions/${sessionId}/classify`,
    {},
  );
  return res.data;
}

// ---------------------------------------------------------------------------
// Delete
// ---------------------------------------------------------------------------

export async function deleteSession(sessionId: string): Promise<void> {
  return apiDelete(`/api/v1/sessions/${sessionId}`);
}
