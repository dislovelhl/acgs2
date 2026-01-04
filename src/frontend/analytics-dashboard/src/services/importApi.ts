/**
 * API Client for Import Endpoints
 *
 * Provides typed client functions for interacting with the import API.
 * Features:
 * - Preview data from external sources
 * - Execute import operations
 * - Track import progress
 * - List and cancel import jobs
 * - Comprehensive error handling
 */

/** API URL from environment */
const API_BASE_URL =
  import.meta.env.VITE_INTEGRATION_API_URL || "http://localhost:8100";

/**
 * Supported external data sources
 */
export type SourceType = "jira" | "servicenow" | "github" | "gitlab";

/**
 * Import operation status
 */
export type ImportStatus =
  | "pending"
  | "validating"
  | "processing"
  | "completed"
  | "failed"
  | "cancelled"
  | "partially_completed";

/**
 * Strategy for handling duplicate items
 */
export type DuplicateHandling = "skip" | "update" | "create_new" | "fail";

/**
 * Configuration for connecting to external source
 */
export interface SourceConfig {
  // Authentication
  api_token?: string;
  api_key?: string;
  username?: string;
  password?: string;
  user_email?: string;

  // Connection settings
  base_url?: string;
  instance?: string;

  // Source-specific filters
  project_key?: string;
  project_keys?: string[];
  repository?: string;
  organization?: string;

  // Data filters
  status_filter?: string[];
  label_filter?: string[];
  date_from?: string;
  date_to?: string;
}

/**
 * Options for controlling import behavior
 */
export interface ImportOptions {
  duplicate_handling?: DuplicateHandling;
  batch_size?: number;
  max_items?: number;
  include_comments?: boolean;
  include_attachments?: boolean;
  include_history?: boolean;
  dry_run?: boolean;
}

/**
 * Request model for import operations
 */
export interface ImportRequest {
  source_type: SourceType;
  source_config: SourceConfig;
  options?: ImportOptions;
  requested_by?: string;
  tenant_id?: string;
  correlation_id?: string;
  tags?: string[];
}

/**
 * Sample item in preview response
 */
export interface PreviewItem {
  external_id: string;
  item_type: string;
  title: string;
  status?: string;
  assignee?: string;
  created_at?: string;
  updated_at?: string;
  labels?: string[];
  metadata?: Record<string, unknown>;
}

/**
 * Preview response from API
 */
export interface PreviewResponse {
  source_type: SourceType;
  total_available: number;
  preview_items: PreviewItem[];
  preview_count: number;
  source_name?: string;
  source_url?: string;
  item_type_counts?: Record<string, number>;
  status_counts?: Record<string, number>;
  warnings?: string[];
}

/**
 * Progress information for import operation
 */
export interface ImportProgress {
  total_items: number;
  processed_items: number;
  successful_items: number;
  failed_items: number;
  skipped_items: number;
  percentage: number;
  estimated_time_remaining?: number;
  current_batch: number;
  total_batches: number;
}

/**
 * Imported item result
 */
export interface ImportedItem {
  external_id: string;
  internal_id?: string;
  item_type: string;
  title: string;
  status: string;
  error_message?: string;
}

/**
 * Import job response from API
 */
export interface ImportResponse {
  job_id: string;
  request_id: string;
  status: ImportStatus;
  source_type: SourceType;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  updated_at: string;
  progress: ImportProgress;
  imported_items?: ImportedItem[];
  error_code?: string;
  error_message?: string;
  error_details?: Record<string, unknown>;
  tenant_id?: string;
  correlation_id?: string;
}

/**
 * Response for listing import jobs
 */
export interface ImportListResponse {
  jobs: ImportResponse[];
  total: number;
  limit: number;
  offset: number;
}

/**
 * Custom error class for API errors
 */
export class ImportApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public details?: unknown
  ) {
    super(message);
    this.name = "ImportApiError";
  }
}

/**
 * Preview data from an external source before importing
 *
 * @param request - Import request configuration
 * @returns Preview response with sample items
 * @throws ImportApiError if preview fails
 */
export async function previewImport(
  request: ImportRequest
): Promise<PreviewResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/imports/preview`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ImportApiError(
        errorData.detail || `Preview failed: ${response.status}`,
        response.status,
        errorData
      );
    }

    const data: PreviewResponse = await response.json();
    return data;
  } catch (err) {
    if (err instanceof ImportApiError) {
      throw err;
    }
    const message =
      err instanceof Error ? err.message : "Failed to preview import";
    throw new ImportApiError(message);
  }
}

/**
 * Execute a data import from an external source
 *
 * @param request - Import request configuration
 * @returns Import job response with job_id for tracking
 * @throws ImportApiError if execution fails
 */
export async function executeImport(
  request: ImportRequest
): Promise<ImportResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/imports`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ImportApiError(
        errorData.detail || `Import execution failed: ${response.status}`,
        response.status,
        errorData
      );
    }

    const data: ImportResponse = await response.json();
    return data;
  } catch (err) {
    if (err instanceof ImportApiError) {
      throw err;
    }
    const message =
      err instanceof Error ? err.message : "Failed to execute import";
    throw new ImportApiError(message);
  }
}

/**
 * Get the status of an import job
 *
 * @param jobId - Unique job identifier
 * @returns Import job response with current status and progress
 * @throws ImportApiError if status check fails
 */
export async function getImportStatus(jobId: string): Promise<ImportResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/imports/${jobId}`, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ImportApiError(
        errorData.detail || `Failed to get import status: ${response.status}`,
        response.status,
        errorData
      );
    }

    const data: ImportResponse = await response.json();
    return data;
  } catch (err) {
    if (err instanceof ImportApiError) {
      throw err;
    }
    const message =
      err instanceof Error ? err.message : "Failed to get import status";
    throw new ImportApiError(message);
  }
}

/**
 * List import jobs with optional filters
 *
 * @param options - Pagination and filter options
 * @returns List of import jobs
 * @throws ImportApiError if listing fails
 */
export async function listImports(options?: {
  status?: ImportStatus;
  source_type?: SourceType;
  limit?: number;
  offset?: number;
}): Promise<ImportListResponse> {
  try {
    const params = new URLSearchParams();
    if (options?.status) params.append("status", options.status);
    if (options?.source_type) params.append("source_type", options.source_type);
    if (options?.limit) params.append("limit", options.limit.toString());
    if (options?.offset) params.append("offset", options.offset.toString());

    const url = `${API_BASE_URL}/api/imports${
      params.toString() ? `?${params.toString()}` : ""
    }`;

    const response = await fetch(url, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ImportApiError(
        errorData.detail || `Failed to list imports: ${response.status}`,
        response.status,
        errorData
      );
    }

    const data: ImportListResponse = await response.json();
    return data;
  } catch (err) {
    if (err instanceof ImportApiError) {
      throw err;
    }
    const message =
      err instanceof Error ? err.message : "Failed to list imports";
    throw new ImportApiError(message);
  }
}

/**
 * Cancel a running import job
 *
 * @param jobId - Unique job identifier
 * @returns Updated import job response
 * @throws ImportApiError if cancellation fails
 */
export async function cancelImport(jobId: string): Promise<ImportResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/imports/${jobId}`, {
      method: "DELETE",
      headers: {
        Accept: "application/json",
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ImportApiError(
        errorData.detail || `Failed to cancel import: ${response.status}`,
        response.status,
        errorData
      );
    }

    const data: ImportResponse = await response.json();
    return data;
  } catch (err) {
    if (err instanceof ImportApiError) {
      throw err;
    }
    const message =
      err instanceof Error ? err.message : "Failed to cancel import";
    throw new ImportApiError(message);
  }
}
