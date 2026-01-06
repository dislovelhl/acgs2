/**
 * Base URL for the Analytics API.
 */
export const ANALYTICS_API_URL =
  import.meta.env.VITE_ANALYTICS_API_URL || "http://localhost:8080";

/**
 * Base URL for the Integration API.
 */
export const INTEGRATION_API_URL =
  import.meta.env.VITE_INTEGRATION_API_URL || "http://localhost:8100";

/**
 * @deprecated Use ANALYTICS_API_URL or INTEGRATION_API_URL instead
 */
export const API_BASE_URL = ANALYTICS_API_URL;
