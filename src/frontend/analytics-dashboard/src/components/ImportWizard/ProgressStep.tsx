/**
 * ProgressStep Component
 *
 * Fourth step of the import wizard - real-time progress tracking.
 * Features:
 * - Initiates import job execution
 * - Real-time progress bar with percentage
 * - Item count tracking (processed/total)
 * - Estimated time remaining
 * - Auto-polling for status updates (every 2 seconds)
 * - Success, error, and in-progress states
 */

import { useCallback, useEffect, useState, useRef } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Loader2,
  TrendingUp,
  XCircle,
} from "lucide-react";
import type { ImportConfig, SourceTool } from "./ImportWizard";

/** Props for ProgressStep component */
export interface ProgressStepProps {
  /** Current import configuration */
  config: ImportConfig;
  /** Callback to update import configuration */
  onConfigUpdate: (updates: Partial<ImportConfig>) => void;
  /** Callback when import completes successfully */
  onComplete?: () => void;
}

/** Import job status from API */
type JobStatus = "pending" | "in_progress" | "completed" | "failed" | "cancelled";

/** Progress data structure */
interface ProgressData {
  job_id: string;
  status: JobStatus;
  progress_percentage: number;
  items_processed: number;
  items_total: number;
  estimated_time_remaining?: number;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
}

/** API URL from environment */
const API_BASE_URL =
  import.meta.env.VITE_INTEGRATION_API_URL || "http://localhost:8100";

/** Polling interval in milliseconds (2 seconds) */
const POLL_INTERVAL_MS = 2000;

/**
 * Formats seconds to human-readable time
 */
function formatTimeRemaining(seconds: number | undefined): string {
  if (!seconds || seconds <= 0) {
    return "Calculating...";
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds % 60);

  if (minutes > 0) {
    return `${minutes}m ${remainingSeconds}s`;
  }
  return `${remainingSeconds}s`;
}

/**
 * Formats a timestamp for display
 */
function formatTimestamp(timestamp: string | undefined): string {
  if (!timestamp) {
    return "N/A";
  }

  try {
    const date = new Date(timestamp);
    return date.toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return timestamp;
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
 * ProgressStep - Real-time import progress tracking
 *
 * Executes the import job and polls for progress updates.
 * Displays progress bar, item counts, and status information.
 */
export function ProgressStep({
  config,
  onConfigUpdate,
  onComplete,
}: ProgressStepProps): JSX.Element {
  const [progressData, setProgressData] = useState<ProgressData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const sourceTool = config.sourceTool;
  const credentials = config.credentials;
  const jobId = config.jobId;

  /**
   * Executes the import job
   */
  const executeImport = useCallback(async () => {
    if (!sourceTool || !credentials) {
      setError("Missing source tool or credentials configuration");
      return;
    }

    setIsExecuting(true);
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

      const response = await fetch(`${API_BASE_URL}/api/imports`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || `Failed to start import: ${response.status}`
        );
      }

      const data = await response.json();
      const newJobId = data.job_id;

      if (!newJobId) {
        throw new Error("No job ID returned from server");
      }

      // Update config with job ID
      onConfigUpdate({ jobId: newJobId });

      // Set initial progress data
      setProgressData({
        job_id: newJobId,
        status: "pending",
        progress_percentage: 0,
        items_processed: 0,
        items_total: config.previewData?.totalCount || 0,
      });
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "Failed to start import. Please try again.";
      setError(message);
    } finally {
      setIsExecuting(false);
    }
  }, [sourceTool, credentials, onConfigUpdate, config.previewData?.totalCount]);

  /**
   * Fetches progress status from API
   */
  const fetchProgress = useCallback(async (currentJobId: string) => {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/imports/${currentJobId}`,
        {
          method: "GET",
          headers: {
            Accept: "application/json",
          },
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || `Failed to fetch progress: ${response.status}`
        );
      }

      const data: ProgressData = await response.json();
      setProgressData(data);

      // Check if job is complete
      if (data.status === "completed" && onComplete) {
        // Stop polling
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
        // Trigger completion callback after a short delay
        setTimeout(onComplete, 1000);
      }

      // Check if job failed
      if (data.status === "failed") {
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
        setError(data.error_message || "Import job failed");
      }
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "Failed to fetch progress. Will retry...";
      console.error("Progress fetch error:", message);
      // Don't set error state for transient network issues during polling
    }
  }, [onComplete]);

  /**
   * Start import job on mount if not already started
   */
  useEffect(() => {
    if (!jobId && !isExecuting && !error) {
      executeImport();
    }
  }, []); // Only run on mount

  /**
   * Set up polling for progress updates
   */
  useEffect(() => {
    if (jobId && !pollingIntervalRef.current) {
      // Fetch immediately
      fetchProgress(jobId);

      // Set up polling interval
      pollingIntervalRef.current = setInterval(() => {
        fetchProgress(jobId);
      }, POLL_INTERVAL_MS);
    }

    // Cleanup on unmount
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, [jobId, fetchProgress]);

  /**
   * Render error state
   */
  if (error && !progressData) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="flex flex-col items-center justify-center py-16">
          <XCircle className="w-16 h-16 text-red-500 mb-4" />
          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            Import Failed
          </h3>
          <p className="text-gray-600 text-center max-w-md mb-6">{error}</p>
          <button
            onClick={executeImport}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
          >
            Retry Import
          </button>
        </div>
      </div>
    );
  }

  /**
   * Render loading state (starting import)
   */
  if (isExecuting || !progressData) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="flex flex-col items-center justify-center py-16">
          <Loader2 className="w-12 h-12 text-blue-600 animate-spin mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Starting Import
          </h3>
          <p className="text-gray-600 text-center max-w-md">
            Initializing import job from {getSourceToolName(sourceTool)}...
          </p>
        </div>
      </div>
    );
  }

  const { status, progress_percentage, items_processed, items_total } =
    progressData;
  const isInProgress = status === "in_progress" || status === "pending";
  const isCompleted = status === "completed";
  const isFailed = status === "failed";

  /**
   * Render progress UI
   */
  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          {isCompleted
            ? "Import Complete"
            : isFailed
              ? "Import Failed"
              : "Importing Data"}
        </h2>
        <p className="text-gray-600">
          {isCompleted
            ? `Successfully imported ${items_processed} items from ${getSourceToolName(sourceTool)}`
            : isFailed
              ? "The import process encountered an error"
              : `Importing data from ${getSourceToolName(sourceTool)}. Please wait...`}
        </p>
      </div>

      {/* Progress Card */}
      <div className="bg-white rounded-lg border border-gray-200 p-8 mb-6">
        {/* Status Icon */}
        <div className="flex items-center justify-center mb-6">
          {isCompleted ? (
            <div className="w-20 h-20 rounded-full bg-green-100 flex items-center justify-center">
              <CheckCircle2 className="w-12 h-12 text-green-600" />
            </div>
          ) : isFailed ? (
            <div className="w-20 h-20 rounded-full bg-red-100 flex items-center justify-center">
              <AlertCircle className="w-12 h-12 text-red-600" />
            </div>
          ) : (
            <div className="w-20 h-20 rounded-full bg-blue-100 flex items-center justify-center">
              <Loader2 className="w-12 h-12 text-blue-600 animate-spin" />
            </div>
          )}
        </div>

        {/* Progress Bar */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">
              Progress
            </span>
            <span className="text-sm font-semibold text-gray-900">
              {Math.round(progress_percentage)}%
            </span>
          </div>
          <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ease-out ${
                isCompleted
                  ? "bg-green-500"
                  : isFailed
                    ? "bg-red-500"
                    : "bg-blue-600"
              }`}
              style={{ width: `${Math.min(progress_percentage, 100)}%` }}
            />
          </div>
        </div>

        {/* Statistics */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          {/* Items Processed */}
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <TrendingUp className="w-6 h-6 text-blue-600 mx-auto mb-2" />
            <div className="text-2xl font-bold text-gray-900">
              {items_processed}
            </div>
            <div className="text-xs text-gray-600 mt-1">
              of {items_total} items
            </div>
          </div>

          {/* Time Remaining */}
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <Clock className="w-6 h-6 text-blue-600 mx-auto mb-2" />
            <div className="text-2xl font-bold text-gray-900">
              {isInProgress
                ? formatTimeRemaining(progressData.estimated_time_remaining)
                : "—"}
            </div>
            <div className="text-xs text-gray-600 mt-1">
              {isInProgress ? "remaining" : "time remaining"}
            </div>
          </div>

          {/* Status */}
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <div className="mb-2">
              {isCompleted ? (
                <CheckCircle2 className="w-6 h-6 text-green-600 mx-auto" />
              ) : isFailed ? (
                <AlertCircle className="w-6 h-6 text-red-600 mx-auto" />
              ) : (
                <Loader2 className="w-6 h-6 text-blue-600 mx-auto animate-spin" />
              )}
            </div>
            <div className="text-lg font-semibold text-gray-900 capitalize">
              {status.replace("_", " ")}
            </div>
            <div className="text-xs text-gray-600 mt-1">current status</div>
          </div>
        </div>

        {/* Error Message */}
        {isFailed && progressData.error_message && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg mb-4">
            <div className="flex gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-semibold text-red-900 mb-1">
                  Error Details
                </h4>
                <p className="text-sm text-red-700">
                  {progressData.error_message}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Timestamps */}
        <div className="pt-4 border-t border-gray-200">
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-gray-600 mb-1">Started At</dt>
              <dd className="text-gray-900 font-medium">
                {formatTimestamp(progressData.started_at)}
              </dd>
            </div>
            {isCompleted && (
              <div>
                <dt className="text-gray-600 mb-1">Completed At</dt>
                <dd className="text-gray-900 font-medium">
                  {formatTimestamp(progressData.completed_at)}
                </dd>
              </div>
            )}
          </dl>
        </div>
      </div>

      {/* Info Box */}
      {isInProgress && (
        <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-sm text-blue-900">
            <strong className="font-semibold">Import in progress.</strong> The
            import is running in the background. You can safely navigate away
            and return later to check the status. Progress is updated every 2
            seconds.
          </p>
        </div>
      )}

      {isCompleted && (
        <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-sm text-green-900">
            <strong className="font-semibold">Import successful!</strong> All
            items have been imported into the system. You can now use the
            imported data in your governance workflows. Click "Finish" to
            complete the wizard.
          </p>
        </div>
      )}

      {isFailed && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-900">
            <strong className="font-semibold">Import failed.</strong> The
            import process encountered an error and could not complete. Please
            review the error message above and try again. Contact support if
            the issue persists.
          </p>
        </div>
      )}
    </div>
  );
}
