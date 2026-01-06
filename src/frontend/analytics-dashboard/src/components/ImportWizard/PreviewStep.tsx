/**
 * PreviewStep Component
 *
 * Third step of the import wizard - data preview before import.
 * Features:
 * - Fetches sample data from the selected source
 * - Displays data in a table format
 * - Shows item count and summary information
 * - Loading and error states
 * - Refresh capability
 */

import { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  FileText,
  Loader2,
  RefreshCw,
  User,
} from "lucide-react";
import type { ImportConfig, SourceTool } from "./ImportWizard";

/** Props for PreviewStep component */
export interface PreviewStepProps {
  /** Current import configuration */
  config: ImportConfig;
  /** Callback to update import configuration */
  onConfigUpdate: (updates: Partial<ImportConfig>) => void;
}

import { INTEGRATION_API_URL, LoadingState } from "../../lib";

/** Preview item structure */
interface PreviewItem {
  id: string;
  title: string;
  status: string;
  assignee?: string;
  createdAt: string;
}

/**
 * Formats a date string for display
 */
function formatDate(dateString: string): string {
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return dateString;
  }
}

/**
 * Gets the display name for a source tool
 */
function getSourceToolName(tool: SourceTool | undefined): string {
  switch (tool) {
    case "jira":
      return "JIRA";
    case "servicenow":
      return "ServiceNow";
    case "github":
      return "GitHub";
    case "gitlab":
      return "GitLab";
    default:
      return "Unknown";
  }
}

/**
 * Gets the item type label based on source tool
 */
function getItemTypeLabel(tool: SourceTool | undefined): string {
  switch (tool) {
    case "jira":
      return "Issues";
    case "servicenow":
      return "Incidents";
    case "github":
      return "Issues & PRs";
    case "gitlab":
      return "Issues & MRs";
    default:
      return "Items";
  }
}

/**
 * PreviewStep - Data preview step
 *
 * Fetches and displays a preview of items that will be imported.
 * Shows a sample of items in a table format with key information.
 */
export function PreviewStep({
  config,
  onConfigUpdate,
}: PreviewStepProps): JSX.Element {
  const [loadingState, setLoadingState] = useState<LoadingState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [previewItems, setPreviewItems] = useState<PreviewItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  const sourceTool = config.sourceTool;
  const credentials = config.credentials;

  /**
   * Fetches preview data from the API
   */
  const fetchPreviewData = useCallback(async () => {
    if (!sourceTool || !credentials) {
      return;
    }

    setLoadingState("loading");
    setError(null);

    try {
      // Build request payload based on source tool
      const requestBody: Record<string, unknown> = {
        source_type: sourceTool,
        source_config: {},
      };

      // Map credentials to source_config based on tool type
      switch (sourceTool) {
        case "jira":
          requestBody.source_config = {
            base_url: credentials.baseUrl,
            username: credentials.username,
            api_token: credentials.apiToken,
            project_key: credentials.projectKey,
          };
          break;
        case "servicenow":
          requestBody.source_config = {
            instance: credentials.instance,
            username: credentials.username,
            password: credentials.password,
          };
          break;
        case "github":
          requestBody.source_config = {
            api_token: credentials.apiToken,
            repository: credentials.repository,
          };
          break;
        case "gitlab":
          requestBody.source_config = {
            base_url: credentials.baseUrl,
            api_token: credentials.apiToken,
            project_path: credentials.projectKey,
          };
          break;
      }

      const response = await fetch(
        `${INTEGRATION_API_URL}/api/imports/preview`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify(requestBody),
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || `Failed to fetch preview: ${response.status}`
        );
      }

      const data = await response.json();

      // Extract items from response
      const items: PreviewItem[] = data.preview_items || [];
      const total = data.total_count || items.length;

      setPreviewItems(items);
      setTotalCount(total);
      setLoadingState("success");

      // Update config with preview data
      onConfigUpdate({
        previewData: {
          items: items.map((item) => ({
            id: item.id,
            title: item.title,
            status: item.status,
            assignee: item.assignee,
            createdAt: item.createdAt,
          })),
          totalCount: total,
        },
      });
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "Failed to fetch preview data. Please check your connection settings.";
      setError(message);
      setLoadingState("error");
    }
  }, [sourceTool, credentials, onConfigUpdate]);

  /**
   * Fetch preview data on mount
   */
  useEffect(() => {
    // Only fetch if we don't already have preview data
    if (!config.previewData && sourceTool && credentials) {
      fetchPreviewData();
    } else if (config.previewData) {
      // Use cached preview data
      setPreviewItems(config.previewData.items);
      setTotalCount(config.previewData.totalCount);
      setLoadingState("success");
    }
  }, []); // Only run on mount

  /**
   * Toggle row expansion
   */
  const toggleRowExpansion = useCallback((itemId: string) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(itemId)) {
        next.delete(itemId);
      } else {
        next.add(itemId);
      }
      return next;
    });
  }, []);

  /**
   * Render loading state
   */
  if (loadingState === "loading") {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="flex flex-col items-center justify-center py-16">
          <Loader2 className="w-12 h-12 text-blue-600 animate-spin mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Fetching Preview Data
          </h3>
          <p className="text-gray-600 text-center max-w-md">
            Connecting to {getSourceToolName(sourceTool)} and retrieving sample
            items. This may take a moment...
          </p>
        </div>
      </div>
    );
  }

  /**
   * Render error state
   */
  if (loadingState === "error" && error) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="flex flex-col items-center justify-center py-16">
          <AlertCircle className="w-12 h-12 text-red-500 mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Failed to Load Preview
          </h3>
          <p className="text-gray-600 text-center max-w-md mb-6">{error}</p>
          <button
            onClick={fetchPreviewData}
            className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
          >
            <RefreshCw className="w-5 h-5" />
            Retry
          </button>
        </div>
      </div>
    );
  }

  /**
   * Render initial/idle state
   */
  if (loadingState === "idle" || !sourceTool) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="text-center py-12">
          <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            No Configuration
          </h3>
          <p className="text-gray-600">
            Please complete the previous steps before previewing data.
          </p>
        </div>
      </div>
    );
  }

  /**
   * Render success state with data table
   */
  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Preview {getSourceToolName(sourceTool)} Data
        </h2>
        <p className="text-gray-600">
          Review the items that will be imported. This is a sample of the first{" "}
          {previewItems.length} {getItemTypeLabel(sourceTool).toLowerCase()}.
        </p>
      </div>

      {/* Summary Card */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-6 mb-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <CheckCircle2 className="w-6 h-6 text-blue-600" />
              <h3 className="text-lg font-semibold text-gray-900">
                Ready to Import
              </h3>
            </div>
            <p className="text-gray-700 mb-3">
              Found <strong className="font-semibold">{totalCount}</strong>{" "}
              {getItemTypeLabel(sourceTool).toLowerCase()} available for import
              from {getSourceToolName(sourceTool)}.
            </p>
            <p className="text-sm text-gray-600">
              Click "Next" to begin the import process. You'll be able to track
              progress in real-time.
            </p>
          </div>
          <button
            onClick={fetchPreviewData}
            className="flex items-center gap-2 px-4 py-2 text-blue-700 hover:bg-blue-100 rounded-lg font-medium transition-colors"
            aria-label="Refresh preview data"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Data Table */}
      {previewItems.length > 0 ? (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          {/* Table Header */}
          <div className="bg-gray-50 border-b border-gray-200 px-6 py-3">
            <div className="grid grid-cols-12 gap-4 text-sm font-medium text-gray-700">
              <div className="col-span-1">
                <FileText className="w-4 h-4" />
              </div>
              <div className="col-span-5">Title</div>
              <div className="col-span-2">Status</div>
              <div className="col-span-2">Assignee</div>
              <div className="col-span-2">Created</div>
            </div>
          </div>

          {/* Table Body */}
          <div className="divide-y divide-gray-200">
            {previewItems.map((item) => {
              const isExpanded = expandedRows.has(item.id);

              return (
                <div
                  key={item.id}
                  className="hover:bg-gray-50 transition-colors"
                >
                  {/* Main Row */}
                  <button
                    onClick={() => toggleRowExpansion(item.id)}
                    className="w-full px-6 py-4 text-left"
                  >
                    <div className="grid grid-cols-12 gap-4 items-center">
                      {/* Expand/Collapse Icon */}
                      <div className="col-span-1">
                        {isExpanded ? (
                          <ChevronUp className="w-4 h-4 text-gray-500" />
                        ) : (
                          <ChevronDown className="w-4 h-4 text-gray-500" />
                        )}
                      </div>

                      {/* Title */}
                      <div className="col-span-5">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {item.title}
                        </p>
                        <p className="text-xs text-gray-500 mt-0.5">
                          ID: {item.id}
                        </p>
                      </div>

                      {/* Status */}
                      <div className="col-span-2">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          {item.status}
                        </span>
                      </div>

                      {/* Assignee */}
                      <div className="col-span-2">
                        {item.assignee ? (
                          <div className="flex items-center gap-1.5 text-sm text-gray-700">
                            <User className="w-3.5 h-3.5 text-gray-400" />
                            <span className="truncate">{item.assignee}</span>
                          </div>
                        ) : (
                          <span className="text-sm text-gray-400">
                            Unassigned
                          </span>
                        )}
                      </div>

                      {/* Created Date */}
                      <div className="col-span-2">
                        <div className="flex items-center gap-1.5 text-sm text-gray-600">
                          <Clock className="w-3.5 h-3.5 text-gray-400" />
                          {formatDate(item.createdAt)}
                        </div>
                      </div>
                    </div>
                  </button>

                  {/* Expanded Details */}
                  {isExpanded && (
                    <div className="px-6 pb-4 bg-gray-50">
                      <div className="ml-8 pl-4 border-l-2 border-gray-300">
                        <dl className="space-y-2">
                          <div>
                            <dt className="text-xs font-medium text-gray-500 uppercase">
                              Full Title
                            </dt>
                            <dd className="text-sm text-gray-900 mt-1">
                              {item.title}
                            </dd>
                          </div>
                          <div>
                            <dt className="text-xs font-medium text-gray-500 uppercase">
                              Item ID
                            </dt>
                            <dd className="text-sm text-gray-900 mt-1 font-mono">
                              {item.id}
                            </dd>
                          </div>
                          <div>
                            <dt className="text-xs font-medium text-gray-500 uppercase">
                              Status
                            </dt>
                            <dd className="text-sm text-gray-900 mt-1">
                              {item.status}
                            </dd>
                          </div>
                          {item.assignee && (
                            <div>
                              <dt className="text-xs font-medium text-gray-500 uppercase">
                                Assigned To
                              </dt>
                              <dd className="text-sm text-gray-900 mt-1">
                                {item.assignee}
                              </dd>
                            </div>
                          )}
                          <div>
                            <dt className="text-xs font-medium text-gray-500 uppercase">
                              Created Date
                            </dt>
                            <dd className="text-sm text-gray-900 mt-1">
                              {formatDate(item.createdAt)}
                            </dd>
                          </div>
                        </dl>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Table Footer */}
          <div className="bg-gray-50 border-t border-gray-200 px-6 py-3">
            <p className="text-sm text-gray-600">
              Showing {previewItems.length} of {totalCount}{" "}
              {getItemTypeLabel(sourceTool).toLowerCase()}
              {totalCount > previewItems.length &&
                ` (${totalCount - previewItems.length} more will be imported)`}
            </p>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
          <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            No Items Found
          </h3>
          <p className="text-gray-600">
            No {getItemTypeLabel(sourceTool).toLowerCase()} were found with the
            current configuration.
          </p>
        </div>
      )}

      {/* Help Text */}
      <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-sm text-blue-900">
          <strong className="font-semibold">What happens next?</strong> When you
          click "Next", the import process will begin. All {totalCount}{" "}
          {getItemTypeLabel(sourceTool).toLowerCase()} will be imported into the
          system. You'll be able to track progress in real-time and cancel if
          needed.
        </p>
      </div>
    </div>
  );
}
