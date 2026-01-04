/**
 * Represents the loading state of a widget component.
 *
 * This type is used across all analytics dashboard widgets to maintain
 * consistent state management during asynchronous data fetching operations.
 *
 * @typedef {('idle'|'loading'|'success'|'error')} LoadingState
 *
 * @property {'idle'} idle - Initial state, no data fetching has occurred
 * @property {'loading'} loading - Data is currently being fetched from the API
 * @property {'success'} success - Data was successfully fetched and is ready to display
 * @property {'error'} error - An error occurred during data fetching
 *
 * @example
 * // Usage in a widget component
 * const [loadingState, setLoadingState] = useState<LoadingState>('idle');
 *
 * const fetchData = async () => {
 *   setLoadingState('loading');
 *   try {
 *     const response = await fetch(`${API_BASE_URL}/endpoint`);
 *     setLoadingState('success');
 *   } catch (error) {
 *     setLoadingState('error');
 *   }
 * };
 *
 * @see {@link API_BASE_URL} for the API configuration used with this type
 */
export type LoadingState = "idle" | "loading" | "success" | "error";
