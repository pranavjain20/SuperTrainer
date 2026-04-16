/**
 * Session Plan API endpoints.
 *
 * Backend routes (plans router has no prefix, paths are explicit):
 *   POST   /api/v1/plans                         → create
 *   POST   /api/v1/plans/parse                   → parse natural language
 *   GET    /api/v1/clients/:clientId/plans        → list by client
 *   GET    /api/v1/plans/:id                      → get
 *   PATCH  /api/v1/plans/:id                      → update
 *   DELETE /api/v1/plans/:id                      → delete
 */

import { apiDelete, apiGet, apiPatch, apiPost } from "./client";
import type {
  DataResponse,
  ListResponse,
  ParsePlanResponse,
  SessionPlan,
  SessionPlanCreate,
  SessionPlanUpdate,
} from "./types";

// ---------------------------------------------------------------------------
// Create
// ---------------------------------------------------------------------------

export async function createPlan(data: SessionPlanCreate): Promise<SessionPlan> {
  const res = await apiPost<DataResponse<SessionPlan>>("/api/v1/plans", data);
  return res.data;
}

// ---------------------------------------------------------------------------
// Parse natural language → structured exercises
// ---------------------------------------------------------------------------

export async function parsePlanText(text: string): Promise<ParsePlanResponse> {
  const res = await apiPost<DataResponse<ParsePlanResponse>>("/api/v1/plans/parse", { text });
  return res.data;
}

// ---------------------------------------------------------------------------
// List by client
// ---------------------------------------------------------------------------

interface PlanListParams {
  cursor?: string;
  limit?: number;
}

export async function getClientPlans(
  clientId: string,
  params?: PlanListParams,
): Promise<ListResponse<SessionPlan>> {
  return apiGet<ListResponse<SessionPlan>>(`/api/v1/clients/${clientId}/plans`, params);
}

// ---------------------------------------------------------------------------
// Single resource
// ---------------------------------------------------------------------------

export async function getPlan(planId: string): Promise<SessionPlan> {
  const res = await apiGet<DataResponse<SessionPlan>>(`/api/v1/plans/${planId}`);
  return res.data;
}

// ---------------------------------------------------------------------------
// Update
// ---------------------------------------------------------------------------

export async function updatePlan(
  planId: string,
  data: SessionPlanUpdate,
): Promise<SessionPlan> {
  const res = await apiPatch<DataResponse<SessionPlan>>(`/api/v1/plans/${planId}`, data);
  return res.data;
}

// ---------------------------------------------------------------------------
// Delete
// ---------------------------------------------------------------------------

export async function deletePlan(planId: string): Promise<void> {
  return apiDelete(`/api/v1/plans/${planId}`);
}
