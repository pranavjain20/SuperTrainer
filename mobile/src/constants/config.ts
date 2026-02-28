/**
 * App configuration.
 *
 * API_BASE_URL points to the FastAPI backend.
 * In development, this is the local machine's IP (not localhost,
 * since the phone is a separate device on the network).
 */
export const API_BASE_URL = __DEV__
  ? "http://192.168.1.160:8000" // Local machine IP (update if network changes)
  : "https://api.supertrainer.app"; // Production URL (Phase 4)
