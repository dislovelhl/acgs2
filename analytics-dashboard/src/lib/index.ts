/**
 * Shared Library - Analytics Dashboard
 *
 * This barrel export provides centralized access to commonly used types and
 * configuration constants for the analytics dashboard widgets. By consolidating
 * these shared definitions, we maintain consistency across all widget components
 * and simplify future maintenance.
 *
 * @module lib
 *
 * @example
 * // Import all shared utilities
 * import { LoadingState, API_BASE_URL } from '@/lib';
 *
 * @example
 * // Import specific items
 * import { API_BASE_URL } from '@/lib';
 * import type { LoadingState } from '@/lib';
 */

/**
 * Re-exports the LoadingState type for widget state management.
 * @see {@link LoadingState} for detailed documentation
 */
export { LoadingState } from "./types";

/**
 * Re-exports the API base URL configuration constant.
 * @see {@link API_BASE_URL} for detailed documentation
 */
export { API_BASE_URL } from "./config";
