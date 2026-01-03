/**
 * Base URL for the Analytics API.
 *
 * This constant provides the root URL for all analytics-related API endpoints.
 * It uses the VITE_ANALYTICS_API_URL environment variable if available,
 * otherwise falls back to the local development server.
 *
 * @constant {string} API_BASE_URL
 * - Production: Set via VITE_ANALYTICS_API_URL environment variable
 * - Development: Defaults to 'http://localhost:8080'
 *
 * @example
 * // Usage in widget components
 * const response = await fetch(`${API_BASE_URL}/predictions`);
 */
export const API_BASE_URL =
  import.meta.env.VITE_ANALYTICS_API_URL || "http://localhost:8080";
