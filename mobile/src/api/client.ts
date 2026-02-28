/**
 * HTTP client for the SuperTrainer API.
 *
 * Thin wrapper around fetch that handles:
 * - Base URL resolution
 * - JSON serialization/deserialization
 * - Query parameter encoding
 * - Multipart upload (voice clips)
 * - Error extraction from our { error: { code, message } } envelope
 *
 * TanStack Query handles retries, caching, and deduplication on top of this.
 */

import { API_BASE_URL } from "@/src/constants/config";
import type { ErrorResponse } from "./types";

// ---------------------------------------------------------------------------
// Error class
// ---------------------------------------------------------------------------

export class ApiError extends Error {
  code: string;
  status: number;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

function buildUrl(path: string, params?: object): string {
  const url = `${API_BASE_URL}${path}`;
  if (!params) return url;

  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value != null) {
      searchParams.append(key, String(value));
    }
  }

  const qs = searchParams.toString();
  return qs ? `${url}?${qs}` : url;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorBody: ErrorResponse | null = null;
    try {
      errorBody = await response.json();
    } catch {
      // Response wasn't JSON — use status text
    }

    const code = errorBody?.error?.code ?? "unknown_error";
    const message = errorBody?.error?.message ?? response.statusText;
    throw new ApiError(response.status, code, message);
  }

  // 204 No Content (e.g., DELETE)
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * GET request. Returns the raw parsed JSON body.
 *
 * For single-resource endpoints that return { data: T, meta: {} },
 * the endpoint function should extract .data.
 * For list endpoints that return { data: T[], meta: PaginationMeta },
 * the endpoint function uses the full response.
 */
export async function apiGet<T>(path: string, params?: object): Promise<T> {
  const response = await fetch(buildUrl(path, params), { method: "GET" });
  return handleResponse<T>(response);
}

/** POST request with JSON body. */
export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(buildUrl(path), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return handleResponse<T>(response);
}

/** PATCH request with JSON body. */
export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(buildUrl(path), {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return handleResponse<T>(response);
}

/** DELETE request. Returns void. */
export async function apiDelete(path: string): Promise<void> {
  const response = await fetch(buildUrl(path), { method: "DELETE" });
  await handleResponse<void>(response);
}

/**
 * POST multipart form data (for file uploads like voice clips).
 * No Content-Type header — fetch sets it automatically with the boundary.
 */
export async function apiUpload<T>(path: string, formData: FormData): Promise<T> {
  const response = await fetch(buildUrl(path), {
    method: "POST",
    body: formData,
  });
  return handleResponse<T>(response);
}
