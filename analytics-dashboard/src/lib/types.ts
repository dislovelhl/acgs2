/**
 * Represents the loading state of a widget component.
 *
 * @typedef {('idle'|'loading'|'success'|'error')} LoadingState
 * - 'idle': Initial state, no data fetching has occurred
 * - 'loading': Data is currently being fetched from the API
 * - 'success': Data was successfully fetched and is ready to display
 * - 'error': An error occurred during data fetching
 */
export type LoadingState = "idle" | "loading" | "success" | "error";
