/**
 * SkipLink Component
 *
 * Accessible skip-to-main-content link for keyboard navigation.
 * Features:
 * - Visually hidden until focused via keyboard
 * - Allows users to bypass navigation and jump to main content
 * - Follows WCAG 2.1 Level A accessibility guidelines (SC 2.4.1)
 * - High z-index ensures visibility when focused
 */

import { ReactNode } from "react";

/**
 * Props for the SkipLink component
 */
interface SkipLinkProps {
  /** The ID of the target element to skip to (e.g., "main-content") */
  targetId: string;
  /** Optional custom label for the skip link */
  label?: string;
  /** Optional children to override the default label */
  children?: ReactNode;
}

/**
 * SkipLink - Accessible skip navigation link
 *
 * Provides a keyboard-accessible link that:
 * - Is the first focusable element on the page
 * - Is visually hidden until focused
 * - Allows users to skip repetitive navigation
 * - Moves focus to the main content area when activated
 *
 * Usage:
 * ```tsx
 * <SkipLink targetId="main-content" />
 * <header>...</header>
 * <main id="main-content">...</main>
 * ```
 */
export function SkipLink({
  targetId,
  label = "Skip to main content",
  children,
}: SkipLinkProps): JSX.Element {
  return (
    <a
      href={`#${targetId}`}
      className="fixed left-0 top-0 z-50 -translate-y-full transform bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-transform focus:translate-y-0"
    >
      {children || label}
    </a>
  );
}

export default SkipLink;
