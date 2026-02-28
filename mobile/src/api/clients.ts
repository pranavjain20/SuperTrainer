/**
 * Client API endpoints.
 *
 * Maps to backend routes in api/clients.py:
 *   GET    /api/v1/clients          → list (cursor pagination, search, archive filter)
 *   POST   /api/v1/clients          → create
 *   GET    /api/v1/clients/:id      → get
 *   PATCH  /api/v1/clients/:id      → update
 */

import { apiGet, apiPatch, apiPost } from "./client";
import type {
  Client,
  ClientCreate,
  ClientUpdate,
  DataResponse,
  ListResponse,
} from "./types";

// ---------------------------------------------------------------------------
// List
// ---------------------------------------------------------------------------

interface ClientListParams {
  cursor?: string;
  limit?: number;
  include_archived?: boolean;
}

export async function getClients(
  params?: ClientListParams,
): Promise<ListResponse<Client>> {
  return apiGet<ListResponse<Client>>("/api/v1/clients", params);
}

// ---------------------------------------------------------------------------
// Single resource
// ---------------------------------------------------------------------------

export async function getClient(id: string): Promise<Client> {
  const res = await apiGet<DataResponse<Client>>(`/api/v1/clients/${id}`);
  return res.data;
}

// ---------------------------------------------------------------------------
// Create
// ---------------------------------------------------------------------------

export async function createClient(data: ClientCreate): Promise<Client> {
  const res = await apiPost<DataResponse<Client>>("/api/v1/clients", data);
  return res.data;
}

// ---------------------------------------------------------------------------
// Update
// ---------------------------------------------------------------------------

export async function updateClient(id: string, data: ClientUpdate): Promise<Client> {
  const res = await apiPatch<DataResponse<Client>>(`/api/v1/clients/${id}`, data);
  return res.data;
}
