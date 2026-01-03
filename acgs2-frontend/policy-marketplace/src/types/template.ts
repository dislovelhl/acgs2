/**
 * TypeScript types for Policy Marketplace
 *
 * These types mirror the Pydantic schemas from the backend
 * Located at: acgs2-core/services/policy_marketplace/app/schemas/template.py
 */

// ====================
// Enums
// ====================

export type TemplateStatus =
  | "draft"
  | "pending_review"
  | "published"
  | "rejected"
  | "archived";

export type TemplateFormat = "json" | "yaml" | "rego";

export type TemplateCategory =
  | "compliance"
  | "access_control"
  | "data_protection"
  | "audit"
  | "rate_limiting"
  | "multi_tenant"
  | "api_security"
  | "data_retention"
  | "custom";

export type AnalyticsEventType = "view" | "download" | "clone";

export type ReviewAction = "approve" | "reject";

// ====================
// Template Types
// ====================

export interface TemplateBase {
  name: string;
  description: string;
  category: TemplateCategory;
  format: TemplateFormat;
}

export interface TemplateCreate extends TemplateBase {
  content: string;
  is_public?: boolean;
  organization_id?: string | null;
}

export interface TemplateUpload {
  file: File;
  name: string;
  description: string;
  category: TemplateCategory;
}

export interface TemplateUpdate {
  name?: string;
  description?: string;
  category?: TemplateCategory;
  content?: string;
  is_public?: boolean;
  status?: TemplateStatus;
}

export interface TemplateResponse extends TemplateBase {
  id: number;
  content: string;
  status: TemplateStatus;
  is_verified: boolean;
  is_public: boolean;
  organization_id: string | null;
  author_id: string | null;
  author_name: string | null;
  current_version: string;
  downloads: number;
  rating: number | null;
  rating_count: number;
  created_at: string;
  updated_at: string;
}

export interface TemplateListItem {
  id: number;
  name: string;
  description: string;
  category: TemplateCategory;
  format: TemplateFormat;
  status: TemplateStatus;
  is_verified: boolean;
  is_public: boolean;
  author_name: string | null;
  current_version: string;
  downloads: number;
  rating: number | null;
  rating_count: number;
  created_at: string;
  updated_at: string;
}

// ====================
// Version Types
// ====================

export interface VersionCreate {
  content: string;
  changelog?: string | null;
}

export interface VersionResponse {
  id: number;
  template_id: number;
  version: string;
  content: string;
  content_hash: string;
  changelog: string | null;
  created_by: string | null;
  created_at: string;
}

export interface VersionListItem {
  id: number;
  version: string;
  changelog: string | null;
  created_by: string | null;
  created_at: string;
}

// ====================
// Rating Types
// ====================

export interface RatingCreate {
  rating: number;
  comment?: string | null;
}

export interface RatingResponse {
  id: number;
  template_id: number;
  user_id: string;
  rating: number;
  comment: string | null;
  created_at: string;
  updated_at: string;
}

// ====================
// Analytics Types
// ====================

export interface AnalyticsEvent {
  event_type: AnalyticsEventType;
  metadata?: Record<string, unknown> | null;
}

export interface AnalyticsResponse {
  id: number;
  template_id: number;
  event_type: string;
  user_id: string | null;
  created_at: string;
}

export interface TemplateAnalyticsSummary {
  template_id: number;
  total_views: number;
  total_downloads: number;
  total_clones: number;
  average_rating: number | null;
  rating_count: number;
}

export interface AnalyticsTrend {
  date: string;
  views: number;
  downloads: number;
}

export interface AnalyticsDashboard {
  start_date: string;
  end_date: string;
  total_templates: number;
  total_downloads: number;
  total_views: number;
  top_templates: TemplateListItem[];
  trends: AnalyticsTrend[];
}

// ====================
// Review Types
// ====================

export interface ReviewRequest {
  action: ReviewAction;
  feedback?: string | null;
}

export interface ReviewResponse {
  template_id: number;
  action: ReviewAction;
  new_status: TemplateStatus;
  reviewed_by: string;
  reviewed_at: string;
  feedback: string | null;
}

export interface ReviewHistoryItem {
  action: string;
  status: TemplateStatus;
  reviewed_by: string | null;
  reviewed_at: string;
  feedback: string | null;
}

// ====================
// Pagination Types
// ====================

export interface PaginationMeta {
  page: number;
  limit: number;
  total_items: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  meta: PaginationMeta;
}

export type TemplateListResponse = PaginatedResponse<TemplateListItem>;
export type VersionListResponse = PaginatedResponse<VersionListItem>;
export type RatingListResponse = PaginatedResponse<RatingResponse>;

// ====================
// Search and Filter Types
// ====================

export interface TemplateSearchParams {
  query?: string;
  category?: TemplateCategory;
  format?: TemplateFormat;
  is_verified?: boolean;
  organization_id?: string;
  page?: number;
  limit?: number;
  sort_by?: "created_at" | "downloads" | "rating" | "name" | "updated_at";
  sort_order?: "asc" | "desc";
}

// ====================
// Error Types
// ====================

export interface ErrorDetail {
  loc: string[];
  msg: string;
  type: string;
}

export interface ErrorResponse {
  detail: string;
  errors?: ErrorDetail[];
}

// ====================
// Message Response
// ====================

export interface MessageResponse {
  message: string;
  success: boolean;
}
