/**
 * Session Entry API endpoints.
 *
 * Backend routes (entries router has no prefix, paths are explicit):
 *   POST   /api/v1/sessions/:sessionId/entries   → create
 *   GET    /api/v1/sessions/:sessionId/entries   → list by session
 *   GET    /api/v1/clients/:clientId/entries      → list by client
 *   GET    /api/v1/entries/:id                    → get
 *   PATCH  /api/v1/entries/:id                    → update (inline edit)
 *   DELETE /api/v1/entries/:id                    → delete
 */

import { apiDelete, apiGet, apiPatch, apiPost } from "./client";
import type {
  DataResponse,
  ListResponse,
  SessionEntry,
  SessionEntryCreate,
  SessionEntryUpdate,
} from "./types";

// ---------------------------------------------------------------------------
// List by session (active session timeline — returns all entries, no pagination)
// ---------------------------------------------------------------------------

export async function getSessionEntries(
  sessionId: string,
): Promise<ListResponse<SessionEntry>> {
  return apiGet<ListResponse<SessionEntry>>(`/api/v1/sessions/${sessionId}/entries`);
}

// ---------------------------------------------------------------------------
// List by client (client profile — all entries across sessions)
// ---------------------------------------------------------------------------

interface ClientEntryParams {
  cursor?: string;
  limit?: number;
}

export async function getClientEntries(
  clientId: string,
  params?: ClientEntryParams,
): Promise<ListResponse<SessionEntry>> {
  return apiGet<ListResponse<SessionEntry>>(
    `/api/v1/clients/${clientId}/entries`,
    params,
  );
}

// ---------------------------------------------------------------------------
// Single resource
// ---------------------------------------------------------------------------

export async function getEntry(entryId: string): Promise<SessionEntry> {
  const res = await apiGet<DataResponse<SessionEntry>>(`/api/v1/entries/${entryId}`);
  return res.data;
}

// ---------------------------------------------------------------------------
// Create
// ---------------------------------------------------------------------------

export async function createEntry(
  sessionId: string,
  data: SessionEntryCreate,
): Promise<SessionEntry> {
  const res = await apiPost<DataResponse<SessionEntry>>(
    `/api/v1/sessions/${sessionId}/entries`,
    data,
  );
  return res.data;
}

// ---------------------------------------------------------------------------
// Update (inline editing on timeline cards)
// ---------------------------------------------------------------------------

export async function updateEntry(
  entryId: string,
  data: SessionEntryUpdate,
): Promise<SessionEntry> {
  const res = await apiPatch<DataResponse<SessionEntry>>(
    `/api/v1/entries/${entryId}`,
    data,
  );
  return res.data;
}

// ---------------------------------------------------------------------------
// Delete
// ---------------------------------------------------------------------------

export async function deleteEntry(entryId: string): Promise<void> {
  return apiDelete(`/api/v1/entries/${entryId}`);
}
