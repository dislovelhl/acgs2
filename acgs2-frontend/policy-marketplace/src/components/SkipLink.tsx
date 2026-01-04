/**
 * ACGS-2 Skip Link Component
 * Constitutional Hash: 018-policy-marketplace
 *
 * Provides a keyboard-accessible skip link for bypassing navigation.
 * Follows WCAG 2.1 Level A Success Criterion 2.4.1 (Bypass Blocks).
 */

import { memo } from "react";

// ====================
// Props Interfaces
// ====================

interface SkipLinkProps {
  /** Target element ID to skip to (e.g., 'main-content') */
  targetId?: string;
  /** Link text for the skip link */
  label?: string;
}

// ====================
// Component
// ====================

/**
 * SkipLink Component
 *
 * A visually hidden link that appears on keyboard focus, allowing users
 * to bypass the header and navigate directly to the main content.
 *
 * @example
 * ```tsx
 * <SkipLink targetId="main-content" />
 * ```
 */
export const SkipLink = memo<SkipLinkProps>(
  ({ targetId = "main-content", label = "Skip to main content" }) => {
    return (
      <a
        href={`#${targetId}`}
        className="skip-link"
        aria-label={label}
      >
        {label}
      </a>
    );
  }
);

SkipLink.displayName = "SkipLink";
