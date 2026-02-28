/**
 * Session Plan API endpoints.
 *
 * Backend routes (plans router has no prefix, paths are explicit):
 *   POST   /api/v1/plans                         → create
 *   GET    /api/v1/clients/:clientId/plans        → list by client
 *   GET    /api/v1/plans/:id                      → get
 *   PATCH  /api/v1/plans/:id                      → update
 *   DELETE /api/v1/plans/:id                      → delete
 */

import { apiDelete, apiGet, apiPatch } from "./client";
import type {
  DataResponse,
  ListResponse,
  SessionPlan,
  SessionPlanUpdate,
} from "./types";

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
