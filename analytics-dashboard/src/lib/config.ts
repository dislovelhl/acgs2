/**
 * Base URL for the Analytics API.
 *
 * This constant provides the root URL for all analytics-related API endpoints
 * across the dashboard. It centralizes API configuration to ensure consistency
 * and simplify environment-based deployment.
 *
 * The URL is determined at build time using Vite's environment variable system.
 * If the VITE_ANALYTICS_API_URL environment variable is set, it will be used;
 * otherwise, the application defaults to the local development server.
 *
 * @constant {string} API_BASE_URL
 *
 * **Environment Configuration:**
 * - **Production**: Set `VITE_ANALYTICS_API_URL` in your `.env.production` file
 * - **Development**: Defaults to `'http://localhost:8080'`
 * - **Testing**: Can be overridden in test environment configuration
 *
 * @example
 * // Basic usage in widget components
 * const response = await fetch(`${API_BASE_URL}/predictions`);
 *
 * @example
 * // Usage with error handling
 * try {
 *   const response = await fetch(`${API_BASE_URL}/anomalies`);
 *   const data = await response.json();
 * } catch (error) {
 *   console.error('Failed to fetch from analytics API:', error);
 * }
 *
 * @example
 * // Usage in test mocks (MSW handlers)
 * import { rest } from 'msw';
 * import { API_BASE_URL } from '../lib';
 *
 * export const handlers = [
 *   rest.get(`${API_BASE_URL}/predictions`, (req, res, ctx) => {
 *     return res(ctx.json({ predictions: [] }));
 *   }),
 * ];
 *
 * @see {@link LoadingState} for managing request states when using this API
 */
export const API_BASE_URL =
  import.meta.env.VITE_ANALYTICS_API_URL || "http://localhost:8080";
