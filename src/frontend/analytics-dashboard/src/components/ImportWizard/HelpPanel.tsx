/**
 * HelpPanel Component
 *
 * Contextual help panel for the import wizard.
 * Features:
 * - Links to pitch guide (exploring the platform)
 * - Links to pilot guide (small team trial)
 * - Links to migration guide (full data migration)
 * - Contact support option
 * - Context-aware recommendations based on import type
 */

import { useEffect, useRef } from "react";
import {
  BookOpen,
  ExternalLink,
  HelpCircle,
  Mail,
  Rocket,
  Users,
  X,
} from "lucide-react";

/** Guide information */
interface Guide {
  /** Guide title */
  title: string;
  /** Guide description */
  description: string;
  /** URL to the guide */
  url: string;
  /** Icon component */
  icon: typeof BookOpen;
  /** Whether this guide is recommended for current context */
  recommended?: boolean;
}

/** Props for HelpPanel component */
export interface HelpPanelProps {
  /** Whether the panel is open */
  isOpen: boolean;
  /** Callback to close the panel */
  onClose: () => void;
  /** Optional context about the import (affects recommendations) */
  importContext?: {
    /** Number of items to import (if known) */
    itemCount?: number;
    /** Source tool being used */
    sourceTool?: string;
  };
}

/** Guide definitions */
const GUIDES: Guide[] = [
  {
    title: "Pitch Guide",
    description:
      "New to ACGS2? Start here to explore the platform and understand how it can help your team.",
    url: "https://docs.acgs2.com/guides/pitch",
    icon: Rocket,
  },
  {
    title: "Pilot Guide",
    description:
      "Ready to try ACGS2 with a small team? This guide helps you run a successful pilot program.",
    url: "https://docs.acgs2.com/guides/pilot",
    icon: Users,
  },
  {
    title: "Migration Guide",
    description:
      "Planning a full migration? Learn best practices for importing large datasets and transitioning your team.",
    url: "https://docs.acgs2.com/guides/migration",
    icon: BookOpen,
  },
];

/**
 * Determines which guide is recommended based on import context
 */
function getRecommendedGuide(
  importContext?: HelpPanelProps["importContext"]
): string | null {
  if (!importContext) {
    return "Pitch Guide"; // Default recommendation
  }

  const { itemCount } = importContext;

  if (!itemCount) {
    return "Pitch Guide";
  }

  // Small import (< 100 items) - recommend pitch/pilot
  if (itemCount < 100) {
    return "Pilot Guide";
  }

  // Medium import (100-1000 items) - recommend pilot
  if (itemCount < 1000) {
    return "Pilot Guide";
  }

  // Large import (1000+ items) - recommend migration
  return "Migration Guide";
}

/**
 * HelpPanel - Contextual help panel with migration guides
 *
 * Displays helpful resources for users going through the import process:
 * - Pitch guide for platform exploration
 * - Pilot guide for small team trials
 * - Migration guide for full data migration
 * - Contact support link
 *
 * Provides context-aware recommendations based on import size/type.
 */
export function HelpPanel({
  isOpen,
  onClose,
  importContext,
}: HelpPanelProps): JSX.Element | null {
  const panelRef = useRef<HTMLDivElement>(null);

  // Determine recommended guide
  const recommendedGuide = getRecommendedGuide(importContext);

  /**
   * Close panel on Escape key
   */
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };

    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [isOpen, onClose]);

  /**
   * Close panel on outside click
   */
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        isOpen &&
        panelRef.current &&
        !panelRef.current.contains(e.target as Node)
      ) {
        onClose();
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen, onClose]);

  // Don't render if not open
  if (!isOpen) {
    return null;
  }

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black bg-opacity-50 z-40 transition-opacity" />

      {/* Panel */}
      <div
        ref={panelRef}
        className="fixed right-0 top-0 h-full w-full max-w-md bg-white shadow-xl z-50 overflow-y-auto"
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <HelpCircle className="w-5 h-5 text-blue-600" />
              <h2 className="text-lg font-semibold text-gray-900">
                Need Help?
              </h2>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
              aria-label="Close help panel"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          <p className="text-sm text-gray-600 mt-2">
            Choose the guide that best fits your needs
          </p>
        </div>

        {/* Content */}
        <div className="px-6 py-6">
          {/* Guides */}
          <div className="space-y-4">
            {GUIDES.map((guide) => {
              const Icon = guide.icon;
              const isRecommended = guide.title === recommendedGuide;

              return (
                <a
                  key={guide.title}
                  href={guide.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`
                    block p-4 rounded-lg border-2 transition-all
                    ${
                      isRecommended
                        ? "border-blue-500 bg-blue-50 hover:bg-blue-100"
                        : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
                    }
                  `}
                >
                  <div className="flex items-start gap-3">
                    <div
                      className={`
                      p-2 rounded-lg
                      ${isRecommended ? "bg-blue-100" : "bg-gray-100"}
                    `}
                    >
                      <Icon
                        className={`w-5 h-5 ${isRecommended ? "text-blue-600" : "text-gray-600"}`}
                      />
                    </div>

                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3
                          className={`font-semibold ${isRecommended ? "text-blue-900" : "text-gray-900"}`}
                        >
                          {guide.title}
                        </h3>
                        {isRecommended && (
                          <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs font-medium rounded">
                            Recommended
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-600 mt-1">
                        {guide.description}
                      </p>
                      <div className="flex items-center gap-1 mt-2 text-sm text-blue-600 font-medium">
                        Read guide
                        <ExternalLink className="w-3 h-3" />
                      </div>
                    </div>
                  </div>
                </a>
              );
            })}
          </div>

          {/* Additional help section */}
          <div className="mt-8 pt-6 border-t border-gray-200">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">
              Need more help?
            </h3>

            <a
              href="mailto:support@acgs2.com"
              className="flex items-center gap-3 p-4 rounded-lg border border-gray-200 hover:border-gray-300 hover:bg-gray-50 transition-all"
            >
              <div className="p-2 rounded-lg bg-gray-100">
                <Mail className="w-5 h-5 text-gray-600" />
              </div>
              <div className="flex-1">
                <h4 className="font-semibold text-gray-900">Contact Support</h4>
                <p className="text-sm text-gray-600">
                  Our team is here to help you get started
                </p>
              </div>
              <ExternalLink className="w-4 h-4 text-gray-400" />
            </a>
          </div>

          {/* Context information */}
          {importContext && (
            <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
              <div className="flex items-start gap-2">
                <HelpCircle className="w-4 h-4 text-blue-600 mt-0.5" />
                <div className="text-sm">
                  <p className="text-blue-900 font-medium">
                    Based on your import
                  </p>
                  <p className="text-blue-700 mt-1">
                    {importContext.itemCount ? (
                      <>
                        You're importing{" "}
                        <strong>{importContext.itemCount.toLocaleString()}</strong>{" "}
                        items
                        {importContext.sourceTool && (
                          <> from {importContext.sourceTool}</>
                        )}
                        . We recommend starting with the{" "}
                        <strong>{recommendedGuide}</strong>.
                      </>
                    ) : (
                      <>
                        We recommend starting with the{" "}
                        <strong>{recommendedGuide}</strong> to get familiar with
                        the platform.
                      </>
                    )}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
