/**
 * Tooltip Component
 *
 * A reusable tooltip component with accessibility support and flexible positioning.
 * Features:
 * - Multiple positioning options (top, bottom, left, right)
 * - Configurable show/hide delays
 * - Full keyboard accessibility with focus support
 * - ARIA attributes for screen readers
 * - Responsive positioning
 *
 * @example
 * ```tsx
 * <Tooltip content="This is helpful information" position="top">
 *   <button>Hover me</button>
 * </Tooltip>
 * ```
 *
 * @example
 * ```tsx
 * <Tooltip content="Quick tip" position="right" delay={500}>
 *   <span>Info icon</span>
 * </Tooltip>
 * ```
 */

import { ReactNode, useEffect, useId, useRef, useState } from "react";

/** Position of the tooltip relative to the trigger element */
export type TooltipPosition = "top" | "bottom" | "left" | "right";

/** Props for the Tooltip component */
export interface TooltipProps {
  /** The content to display inside the tooltip */
  content: ReactNode;
  /** The element that triggers the tooltip on hover/focus */
  children: ReactNode;
  /** Position of the tooltip relative to the trigger element */
  position?: TooltipPosition;
  /** Delay in milliseconds before showing the tooltip (default: 200ms) */
  delay?: number;
  /** Delay in milliseconds before hiding the tooltip (default: 0ms) */
  hideDelay?: number;
  /** Additional CSS classes for the tooltip container */
  className?: string;
  /** Whether the tooltip is disabled */
  disabled?: boolean;
}

/**
 * Returns Tailwind CSS classes for positioning the tooltip
 */
function getPositionClasses(position: TooltipPosition): string {
  const baseClasses = "absolute z-50";

  switch (position) {
    case "top":
      return `${baseClasses} bottom-full left-1/2 -translate-x-1/2 -translate-y-2`;
    case "bottom":
      return `${baseClasses} top-full left-1/2 -translate-x-1/2 translate-y-2`;
    case "left":
      return `${baseClasses} right-full top-1/2 -translate-x-2 -translate-y-1/2`;
    case "right":
      return `${baseClasses} left-full top-1/2 translate-x-2 -translate-y-1/2`;
  }
}

/**
 * Returns Tailwind CSS classes for the tooltip arrow
 */
function getArrowClasses(position: TooltipPosition): string {
  const baseClasses = "absolute h-2 w-2 rotate-45 bg-gray-900";

  switch (position) {
    case "top":
      return `${baseClasses} -bottom-1 left-1/2 -translate-x-1/2`;
    case "bottom":
      return `${baseClasses} -top-1 left-1/2 -translate-x-1/2`;
    case "left":
      return `${baseClasses} -right-1 top-1/2 -translate-y-1/2`;
    case "right":
      return `${baseClasses} -left-1 top-1/2 -translate-y-1/2`;
  }
}

/**
 * Tooltip - A reusable tooltip component with accessibility support
 *
 * Provides contextual help on hover or focus. Supports multiple positions,
 * configurable delays, and full keyboard accessibility.
 *
 * Accessibility features:
 * - role="tooltip" for screen reader identification
 * - aria-describedby links trigger to tooltip content
 * - Keyboard focus support (shows on focus, hides on blur)
 * - Semantic HTML structure
 *
 * @component
 */
export function Tooltip({
  content,
  children,
  position = "top",
  delay = 200,
  hideDelay = 0,
  className = "",
  disabled = false,
}: TooltipProps): JSX.Element {
  const [isVisible, setIsVisible] = useState(false);
  const showTimeoutRef = useRef<number | null>(null);
  const hideTimeoutRef = useRef<number | null>(null);
  const tooltipId = useId();

  /**
   * Clear any pending show/hide timeouts
   */
  const clearTimeouts = () => {
    if (showTimeoutRef.current !== null) {
      window.clearTimeout(showTimeoutRef.current);
      showTimeoutRef.current = null;
    }
    if (hideTimeoutRef.current !== null) {
      window.clearTimeout(hideTimeoutRef.current);
      hideTimeoutRef.current = null;
    }
  };

  /**
   * Show the tooltip after the configured delay
   */
  const handleShow = () => {
    if (disabled) return;

    clearTimeouts();
    showTimeoutRef.current = window.setTimeout(() => {
      setIsVisible(true);
    }, delay);
  };

  /**
   * Hide the tooltip after the configured delay
   */
  const handleHide = () => {
    clearTimeouts();
    if (hideDelay > 0) {
      hideTimeoutRef.current = window.setTimeout(() => {
        setIsVisible(false);
      }, hideDelay);
    } else {
      setIsVisible(false);
    }
  };

  /**
   * Clean up timeouts on unmount
   */
  useEffect(() => {
    return () => {
      clearTimeouts();
    };
  }, []);

  return (
    <div className="relative inline-block">
      {/* Trigger Element */}
      <div
        onMouseEnter={handleShow}
        onMouseLeave={handleHide}
        onFocus={handleShow}
        onBlur={handleHide}
        aria-describedby={isVisible ? tooltipId : undefined}
        className="inline-block"
      >
        {children}
      </div>

      {/* Tooltip Content */}
      {isVisible && !disabled && (
        <div
          id={tooltipId}
          role="tooltip"
          className={`${getPositionClasses(position)} ${className}`}
        >
          <div className="relative rounded-md bg-gray-900 px-3 py-2 text-sm text-white shadow-lg">
            {content}
            {/* Arrow */}
            <div className={getArrowClasses(position)} aria-hidden="true" />
          </div>
        </div>
      )}
    </div>
  );
}

export default Tooltip;
