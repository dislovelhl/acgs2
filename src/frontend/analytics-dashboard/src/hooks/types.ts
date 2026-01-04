/**
 * Analytics Dashboard Hook Types
 *
 * Shared type definitions for React hooks in the analytics dashboard
 */

/**
 * Standard return type for data-fetching hooks
 *
 * @template T - The type of data being fetched
 */
export interface UseDataResult<T> {
  /** The fetched data, or null if not yet loaded or if an error occurred */
  data: T | null;
  /** Whether the data is currently being fetched */
  loading: boolean;
  /** Any error that occurred during fetching, or null if successful */
  error: Error | null;
  /** Function to manually refetch the data */
  refetch: () => Promise<void>;
}
