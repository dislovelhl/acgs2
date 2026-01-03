/**
 * ACGS-2 Policy Marketplace API Client
 *
 * Client for communicating with the Policy Marketplace backend service.
 * Follows patterns from acgs2-observability/monitoring/dashboard/src/utils/api.ts
 */

import type {
  TemplateResponse,
  TemplateCreate,
  TemplateUpdate,
  TemplateListResponse,
  TemplateSearchParams,
  VersionResponse,
  VersionCreate,
  VersionListResponse,
  RatingCreate,
  RatingResponse,
  RatingListResponse,
  AnalyticsEvent,
  AnalyticsDashboard,
  TemplateAnalyticsSummary,
  AnalyticsTrend,
  ReviewResponse,
  ReviewHistoryItem,
  TemplateCategory,
  MessageResponse,
} from "@types/template";

const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8003/api/v1";

/**
 * Custom error class for API errors
 */
export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public detail?: string
  ) {
    super(detail || `API Error: ${status} ${statusText}`);
    this.name = "ApiError";
  }
}

/**
 * Policy Marketplace API client
 */
export class MarketplaceAPI {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Make a fetch request with error handling
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });

    if (!response.ok) {
      let detail: string | undefined;
      try {
        const errorBody = await response.json();
        detail = errorBody.detail || JSON.stringify(errorBody);
      } catch {
        detail = await response.text();
      }
      throw new ApiError(response.status, response.statusText, detail);
    }

    return response.json();
  }

  // ====================
  // Template Endpoints
  // ====================

  /**
   * List templates with optional filtering and pagination
   */
  async listTemplates(
    params: TemplateSearchParams = {}
  ): Promise<TemplateListResponse> {
    const searchParams = new URLSearchParams();

    if (params.query) searchParams.set("query", params.query);
    if (params.category) searchParams.set("category", params.category);
    if (params.format) searchParams.set("format", params.format);
    if (params.is_verified !== undefined)
      searchParams.set("is_verified", String(params.is_verified));
    if (params.organization_id)
      searchParams.set("organization_id", params.organization_id);
    if (params.page) searchParams.set("page", String(params.page));
    if (params.limit) searchParams.set("limit", String(params.limit));
    if (params.sort_by) searchParams.set("sort_by", params.sort_by);
    if (params.sort_order) searchParams.set("sort_order", params.sort_order);

    const queryString = searchParams.toString();
    const endpoint = queryString ? `/templates?${queryString}` : "/templates";

    return this.request<TemplateListResponse>(endpoint);
  }

  /**
   * Get a single template by ID
   */
  async getTemplate(id: number): Promise<TemplateResponse> {
    return this.request<TemplateResponse>(`/templates/${id}`);
  }

  /**
   * Create a new template
   */
  async createTemplate(data: TemplateCreate): Promise<TemplateResponse> {
    return this.request<TemplateResponse>("/templates", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  /**
   * Update an existing template
   */
  async updateTemplate(
    id: number,
    data: TemplateUpdate
  ): Promise<TemplateResponse> {
    return this.request<TemplateResponse>(`/templates/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  /**
   * Delete a template (soft delete)
   */
  async deleteTemplate(id: number): Promise<MessageResponse> {
    return this.request<MessageResponse>(`/templates/${id}`, {
      method: "DELETE",
    });
  }

  /**
   * Upload a template file
   */
  async uploadTemplate(
    file: File,
    name: string,
    description: string,
    category: TemplateCategory
  ): Promise<TemplateResponse> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("name", name);
    formData.append("description", description);
    formData.append("category", category);

    const url = `${this.baseUrl}/templates/upload`;
    const response = await fetch(url, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      let detail: string | undefined;
      try {
        const errorBody = await response.json();
        detail = errorBody.detail || JSON.stringify(errorBody);
      } catch {
        detail = await response.text();
      }
      throw new ApiError(response.status, response.statusText, detail);
    }

    return response.json();
  }

  /**
   * Download a template file
   */
  async downloadTemplate(id: number): Promise<Blob> {
    const url = `${this.baseUrl}/templates/${id}/download`;
    const response = await fetch(url);

    if (!response.ok) {
      throw new ApiError(
        response.status,
        response.statusText,
        `Failed to download template: ${response.statusText}`
      );
    }

    return response.blob();
  }

  // ====================
  // Version Endpoints
  // ====================

  /**
   * List versions for a template
   */
  async listVersions(
    templateId: number,
    page = 1,
    limit = 20
  ): Promise<VersionListResponse> {
    return this.request<VersionListResponse>(
      `/templates/${templateId}/versions?page=${page}&limit=${limit}`
    );
  }

  /**
   * Create a new version for a template
   */
  async createVersion(
    templateId: number,
    data: VersionCreate
  ): Promise<VersionResponse> {
    return this.request<VersionResponse>(`/templates/${templateId}/versions`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  /**
   * Get a specific version
   */
  async getVersion(
    templateId: number,
    versionId: number
  ): Promise<VersionResponse> {
    return this.request<VersionResponse>(
      `/templates/${templateId}/versions/${versionId}`
    );
  }

  /**
   * Get the latest version for a template
   */
  async getLatestVersion(templateId: number): Promise<VersionResponse> {
    return this.request<VersionResponse>(
      `/templates/${templateId}/versions/latest`
    );
  }

  // ====================
  // Rating Endpoints
  // ====================

  /**
   * Rate a template
   */
  async rateTemplate(
    templateId: number,
    data: RatingCreate
  ): Promise<RatingResponse> {
    return this.request<RatingResponse>(
      `/analytics/templates/${templateId}/rate`,
      {
        method: "POST",
        body: JSON.stringify(data),
      }
    );
  }

  /**
   * List ratings for a template
   */
  async listRatings(
    templateId: number,
    page = 1,
    limit = 20
  ): Promise<RatingListResponse> {
    return this.request<RatingListResponse>(
      `/analytics/templates/${templateId}/ratings?page=${page}&limit=${limit}`
    );
  }

  // ====================
  // Analytics Endpoints
  // ====================

  /**
   * Get analytics dashboard data
   */
  async getAnalyticsDashboard(
    startDate?: string,
    endDate?: string
  ): Promise<AnalyticsDashboard> {
    const params = new URLSearchParams();
    if (startDate) params.set("start_date", startDate);
    if (endDate) params.set("end_date", endDate);

    const queryString = params.toString();
    const endpoint = queryString
      ? `/analytics/templates?${queryString}`
      : "/analytics/templates";

    return this.request<AnalyticsDashboard>(endpoint);
  }

  /**
   * Get analytics summary for a specific template
   */
  async getTemplateAnalytics(
    templateId: number
  ): Promise<TemplateAnalyticsSummary> {
    return this.request<TemplateAnalyticsSummary>(
      `/analytics/templates/${templateId}`
    );
  }

  /**
   * Track an analytics event
   */
  async trackEvent(templateId: number, event: AnalyticsEvent): Promise<void> {
    await this.request<MessageResponse>(
      `/analytics/templates/${templateId}/track`,
      {
        method: "POST",
        body: JSON.stringify(event),
      }
    );
  }

  /**
   * Get analytics trends
   */
  async getAnalyticsTrends(
    startDate?: string,
    endDate?: string
  ): Promise<AnalyticsTrend[]> {
    const params = new URLSearchParams();
    if (startDate) params.set("start_date", startDate);
    if (endDate) params.set("end_date", endDate);

    const queryString = params.toString();
    const endpoint = queryString
      ? `/analytics/trends?${queryString}`
      : "/analytics/trends";

    return this.request<AnalyticsTrend[]>(endpoint);
  }

  // ====================
  // Review Endpoints
  // ====================

  /**
   * Submit a template for review
   */
  async submitForReview(templateId: number): Promise<TemplateResponse> {
    return this.request<TemplateResponse>(`/reviews/submit/${templateId}`, {
      method: "POST",
    });
  }

  /**
   * Get pending reviews (admin only)
   */
  async getPendingReviews(): Promise<TemplateListResponse> {
    return this.request<TemplateListResponse>("/reviews/pending");
  }

  /**
   * Approve a template (admin only)
   */
  async approveTemplate(
    templateId: number,
    feedback?: string
  ): Promise<ReviewResponse> {
    return this.request<ReviewResponse>(`/reviews/${templateId}/approve`, {
      method: "POST",
      body: JSON.stringify({ feedback }),
    });
  }

  /**
   * Reject a template (admin only)
   */
  async rejectTemplate(
    templateId: number,
    feedback?: string
  ): Promise<ReviewResponse> {
    return this.request<ReviewResponse>(`/reviews/${templateId}/reject`, {
      method: "POST",
      body: JSON.stringify({ feedback }),
    });
  }

  /**
   * Get review history for a template
   */
  async getReviewHistory(templateId: number): Promise<ReviewHistoryItem[]> {
    return this.request<ReviewHistoryItem[]>(`/reviews/${templateId}/history`);
  }

  /**
   * Resubmit a rejected template for review
   */
  async resubmitForReview(templateId: number): Promise<TemplateResponse> {
    return this.request<TemplateResponse>(`/reviews/${templateId}/resubmit`, {
      method: "POST",
    });
  }

  // ====================
  // Health Check
  // ====================

  /**
   * Check API health
   */
  async healthCheck(): Promise<{ status: string }> {
    // Health endpoint is at root, not under /api/v1
    const baseWithoutVersion = this.baseUrl.replace(/\/api\/v1$/, "");
    const response = await fetch(`${baseWithoutVersion}/health`);

    if (!response.ok) {
      throw new ApiError(
        response.status,
        response.statusText,
        "Health check failed"
      );
    }

    return response.json();
  }
}

// Default API instance
export const marketplaceAPI = new MarketplaceAPI();
