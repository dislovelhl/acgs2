/**
 * LoadingOverlay Component
 *
 * A reusable overlay component that displays a loading spinner with a semi-transparent
 * background. Used to indicate loading state while keeping underlying content visible.
 *
 * @example
 * ```tsx
 * <div className="relative">
 *   <LoadingOverlay show={isLoading} message="Refreshing data..." />
 *   <YourContent />
 * </div>
 * ```
 */

import { RefreshCw } from "lucide-react";

interface LoadingOverlayProps {
  /** Controls whether the overlay is visible */
  show: boolean;
  /** Optional loading message to display below the spinner */
  message?: string;
}

/**
 * LoadingOverlay - Displays a semi-transparent overlay with a centered spinner
 *
 * Features:
 * - Semi-transparent white background that preserves underlying content visibility
 * - Centered animated spinner
 * - Optional custom loading message
 * - Proper ARIA labels for accessibility
 * - Positioned absolutely to overlay parent container (parent must have position: relative)
 *
 * @param props - Component props
 * @param props.show - Controls visibility of the overlay
 * @param props.message - Optional message to display below spinner (default: "Loading...")
 */
export function LoadingOverlay({
  show,
  message = "Loading...",
}: LoadingOverlayProps): JSX.Element | null {
  // Don't render anything if not shown
  if (!show) {
    return null;
  }

  return (
    <div
      className="absolute inset-0 z-10 flex items-center justify-center rounded-lg bg-white/50 backdrop-blur-[1px]"
      role="status"
      aria-live="polite"
      aria-label="Loading"
    >
      <div className="flex flex-col items-center gap-2">
        <RefreshCw
          className="h-8 w-8 animate-spin text-gray-600"
          aria-hidden="true"
        />
        {message && (
          <p className="text-sm font-medium text-gray-700">{message}</p>
        )}
      </div>
    </div>
  );
}

export default LoadingOverlay;
