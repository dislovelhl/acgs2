/**
 * ACGS-2 Template List Component
 * Constitutional Hash: 018-policy-marketplace
 *
 * Displays policy templates in a browsable grid with filtering and search.
 * Optimized with React.memo and useMemo for performance.
 */

import { memo, useMemo, useState, useCallback, useEffect } from "react";
import { marketplaceAPI, ApiError } from "@services/api";
import type {
  TemplateListItem,
  TemplateCategory,
  TemplateFormat,
  TemplateSearchParams,
  PaginationMeta,
} from "@types/template";

// ====================
// Props Interfaces
// ====================

interface TemplateListProps {
  /** Callback when a template is selected */
  onTemplateSelect?: (template: TemplateListItem) => void;
  /** Initial search params */
  initialParams?: TemplateSearchParams;
}

// ====================
// Static Constants
// ====================

const categoryLabels: Record<TemplateCategory, string> = {
  compliance: "Compliance",
  access_control: "Access Control",
  data_protection: "Data Protection",
  audit: "Audit",
  rate_limiting: "Rate Limiting",
  multi_tenant: "Multi-Tenant",
  api_security: "API Security",
  data_retention: "Data Retention",
  custom: "Custom",
} as const;

const categoryStyles: Record<TemplateCategory, string> = {
  compliance: "bg-blue-100 text-blue-800",
  access_control: "bg-purple-100 text-purple-800",
  data_protection: "bg-green-100 text-green-800",
  audit: "bg-yellow-100 text-yellow-800",
  rate_limiting: "bg-orange-100 text-orange-800",
  multi_tenant: "bg-pink-100 text-pink-800",
  api_security: "bg-red-100 text-red-800",
  data_retention: "bg-teal-100 text-teal-800",
  custom: "bg-gray-100 text-gray-800",
} as const;

const formatLabels: Record<TemplateFormat, string> = {
  json: "JSON",
  yaml: "YAML",
  rego: "Rego",
} as const;

const sortOptions = [
  { value: "created_at", label: "Newest" },
  { value: "downloads", label: "Most Downloaded" },
  { value: "rating", label: "Highest Rated" },
  { value: "name", label: "Name" },
] as const;

// ====================
// Helper Functions
// ====================

const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
};

// ====================
// Loading Skeleton
// ====================

const TemplateListSkeleton = memo(function TemplateListSkeleton() {
  return (
    <div className="space-y-4">
      {/* Search skeleton */}
      <div className="h-10 bg-gray-200 rounded animate-pulse" />

      {/* Filter skeleton */}
      <div className="flex gap-2">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-8 w-24 bg-gray-200 rounded animate-pulse" />
        ))}
      </div>

      {/* Grid skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="h-48 bg-gray-200 rounded-lg animate-pulse" />
        ))}
      </div>
    </div>
  );
});

// ====================
// Empty State
// ====================

const EmptyTemplatesState = memo(function EmptyTemplatesState() {
  return (
    <div className="text-center py-12 text-gray-500">
      <svg
        className="w-16 h-16 mx-auto mb-4 text-gray-300"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
        />
      </svg>
      <p className="text-lg font-medium">No templates found</p>
      <p className="text-sm text-gray-400 mt-1">
        Try adjusting your search or filters
      </p>
    </div>
  );
});

// ====================
// Error State
// ====================

interface ErrorStateProps {
  error: string;
  onRetry: () => void;
}

const ErrorState = memo(function ErrorState({ error, onRetry }: ErrorStateProps) {
  return (
    <div className="text-center py-12">
      <svg
        className="w-16 h-16 mx-auto mb-4 text-red-400"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
        />
      </svg>
      <p className="text-lg font-medium text-gray-900">Failed to load templates</p>
      <p className="text-sm text-red-600 mt-1">{error}</p>
      <button
        onClick={onRetry}
        className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
      >
        Try Again
      </button>
    </div>
  );
});

// ====================
// Template Card
// ====================

interface TemplateCardProps {
  template: TemplateListItem;
  onClick?: (template: TemplateListItem) => void;
}

const TemplateCard = memo(function TemplateCard({
  template,
  onClick,
}: TemplateCardProps) {
  const formattedDate = useMemo(
    () => formatDate(template.created_at),
    [template.created_at]
  );

  const handleClick = useCallback(() => {
    onClick?.(template);
  }, [onClick, template]);

  return (
    <div
      onClick={handleClick}
      className="
        bg-white rounded-lg border border-gray-200 p-5 shadow-sm
        hover:border-blue-300 hover:shadow-md transition-all duration-200
        cursor-pointer
      "
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-3">
        <h3 className="font-semibold text-gray-900 truncate flex-1">
          {template.name}
        </h3>
        {template.is_verified && (
          <span className="flex-shrink-0" title="Verified Template">
            <svg
              className="w-5 h-5 text-blue-600"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clipRule="evenodd"
              />
            </svg>
          </span>
        )}
      </div>

      {/* Description */}
      <p className="text-sm text-gray-600 line-clamp-2 mb-3 min-h-[40px]">
        {template.description}
      </p>

      {/* Tags */}
      <div className="flex flex-wrap gap-2 mb-3">
        <span
          className={`px-2 py-0.5 text-xs font-medium rounded ${categoryStyles[template.category]}`}
        >
          {categoryLabels[template.category]}
        </span>
        <span className="px-2 py-0.5 text-xs font-medium rounded bg-gray-100 text-gray-700">
          {formatLabels[template.format]}
        </span>
        <span className="px-2 py-0.5 text-xs font-medium rounded bg-gray-100 text-gray-700">
          v{template.current_version}
        </span>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between text-sm text-gray-500 pt-3 border-t border-gray-100">
        <div className="flex items-center gap-4">
          {/* Downloads */}
          <span className="flex items-center gap-1">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
              />
            </svg>
            {template.downloads}
          </span>

          {/* Rating */}
          {template.rating !== null && (
            <span className="flex items-center gap-1">
              <svg className="w-4 h-4 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
              {template.rating.toFixed(1)}
            </span>
          )}
        </div>

        <span className="text-xs">{formattedDate}</span>
      </div>
    </div>
  );
});

// ====================
// Pagination
// ====================

interface PaginationProps {
  meta: PaginationMeta;
  onPageChange: (page: number) => void;
}

const Pagination = memo(function Pagination({ meta, onPageChange }: PaginationProps) {
  const handlePrevious = useCallback(() => {
    if (meta.has_prev) {
      onPageChange(meta.page - 1);
    }
  }, [meta.has_prev, meta.page, onPageChange]);

  const handleNext = useCallback(() => {
    if (meta.has_next) {
      onPageChange(meta.page + 1);
    }
  }, [meta.has_next, meta.page, onPageChange]);

  if (meta.total_pages <= 1) return null;

  return (
    <div className="flex items-center justify-between py-4 border-t border-gray-200">
      <div className="text-sm text-gray-500">
        Showing {(meta.page - 1) * meta.limit + 1} -{" "}
        {Math.min(meta.page * meta.limit, meta.total_items)} of {meta.total_items} templates
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={handlePrevious}
          disabled={!meta.has_prev}
          className="
            px-3 py-1.5 text-sm font-medium rounded-md border
            disabled:opacity-50 disabled:cursor-not-allowed
            enabled:hover:bg-gray-50 transition-colors
          "
        >
          Previous
        </button>
        <span className="text-sm text-gray-600">
          Page {meta.page} of {meta.total_pages}
        </span>
        <button
          onClick={handleNext}
          disabled={!meta.has_next}
          className="
            px-3 py-1.5 text-sm font-medium rounded-md border
            disabled:opacity-50 disabled:cursor-not-allowed
            enabled:hover:bg-gray-50 transition-colors
          "
        >
          Next
        </button>
      </div>
    </div>
  );
});

// ====================
// Search and Filters
// ====================

interface SearchFiltersProps {
  params: TemplateSearchParams;
  onParamsChange: (params: TemplateSearchParams) => void;
}

const SearchFilters = memo(function SearchFilters({
  params,
  onParamsChange,
}: SearchFiltersProps) {
  const [searchInput, setSearchInput] = useState(params.query || "");

  const handleSearchSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      onParamsChange({ ...params, query: searchInput, page: 1 });
    },
    [params, searchInput, onParamsChange]
  );

  const handleCategoryChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      const category = e.target.value as TemplateCategory | "";
      onParamsChange({
        ...params,
        category: category || undefined,
        page: 1,
      });
    },
    [params, onParamsChange]
  );

  const handleFormatChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      const format = e.target.value as TemplateFormat | "";
      onParamsChange({
        ...params,
        format: format || undefined,
        page: 1,
      });
    },
    [params, onParamsChange]
  );

  const handleSortChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      const sortBy = e.target.value as TemplateSearchParams["sort_by"];
      onParamsChange({
        ...params,
        sort_by: sortBy,
        sort_order: sortBy === "name" ? "asc" : "desc",
        page: 1,
      });
    },
    [params, onParamsChange]
  );

  const handleVerifiedToggle = useCallback(() => {
    onParamsChange({
      ...params,
      is_verified: params.is_verified ? undefined : true,
      page: 1,
    });
  }, [params, onParamsChange]);

  const handleClearFilters = useCallback(() => {
    setSearchInput("");
    onParamsChange({ page: 1, limit: params.limit });
  }, [params.limit, onParamsChange]);

  const hasActiveFilters = useMemo(() => {
    return !!(
      params.query ||
      params.category ||
      params.format ||
      params.is_verified
    );
  }, [params]);

  return (
    <div className="space-y-4">
      {/* Search Bar */}
      <form onSubmit={handleSearchSubmit} className="flex gap-2">
        <div className="relative flex-1">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search templates..."
            className="
              w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md
              focus:ring-2 focus:ring-blue-500 focus:border-blue-500
              transition-colors
            "
          />
        </div>
        <button
          type="submit"
          className="
            px-4 py-2 bg-blue-600 text-white rounded-md
            hover:bg-blue-700 transition-colors
          "
        >
          Search
        </button>
      </form>

      {/* Filters Row */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Category Filter */}
        <select
          value={params.category || ""}
          onChange={handleCategoryChange}
          className="
            px-3 py-1.5 border border-gray-300 rounded-md text-sm
            focus:ring-2 focus:ring-blue-500 focus:border-blue-500
          "
        >
          <option value="">All Categories</option>
          {Object.entries(categoryLabels).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>

        {/* Format Filter */}
        <select
          value={params.format || ""}
          onChange={handleFormatChange}
          className="
            px-3 py-1.5 border border-gray-300 rounded-md text-sm
            focus:ring-2 focus:ring-blue-500 focus:border-blue-500
          "
        >
          <option value="">All Formats</option>
          {Object.entries(formatLabels).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>

        {/* Sort */}
        <select
          value={params.sort_by || "created_at"}
          onChange={handleSortChange}
          className="
            px-3 py-1.5 border border-gray-300 rounded-md text-sm
            focus:ring-2 focus:ring-blue-500 focus:border-blue-500
          "
        >
          {sortOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>

        {/* Verified Toggle */}
        <button
          onClick={handleVerifiedToggle}
          className={`
            px-3 py-1.5 text-sm font-medium rounded-md border
            transition-colors
            ${
              params.is_verified
                ? "bg-blue-100 border-blue-300 text-blue-800"
                : "bg-white border-gray-300 text-gray-700 hover:bg-gray-50"
            }
          `}
        >
          <span className="flex items-center gap-1">
            <svg
              className="w-4 h-4"
              fill={params.is_verified ? "currentColor" : "none"}
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
              />
            </svg>
            Verified Only
          </span>
        </button>

        {/* Clear Filters */}
        {hasActiveFilters && (
          <button
            onClick={handleClearFilters}
            className="
              px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900
              transition-colors
            "
          >
            Clear filters
          </button>
        )}
      </div>
    </div>
  );
});

// ====================
// Main Component
// ====================

function TemplateListComponent({
  onTemplateSelect,
  initialParams = {},
}: TemplateListProps): JSX.Element {
  // State
  const [templates, setTemplates] = useState<TemplateListItem[]>([]);
  const [meta, setMeta] = useState<PaginationMeta | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [params, setParams] = useState<TemplateSearchParams>({
    page: 1,
    limit: 12,
    sort_by: "created_at",
    sort_order: "desc",
    ...initialParams,
  });

  // Fetch templates
  const fetchTemplates = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await marketplaceAPI.listTemplates(params);
      setTemplates(response.items);
      setMeta(response.meta);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail || err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("An unexpected error occurred");
      }
    } finally {
      setLoading(false);
    }
  }, [params]);

  // Load templates on mount and when params change
  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  // Handlers
  const handleParamsChange = useCallback((newParams: TemplateSearchParams) => {
    setParams(newParams);
  }, []);

  const handlePageChange = useCallback((page: number) => {
    setParams((prev) => ({ ...prev, page }));
  }, []);

  const handleRetry = useCallback(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  // Render loading state
  if (loading && templates.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
        <TemplateListSkeleton />
      </div>
    );
  }

  // Render error state
  if (error && templates.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
        <ErrorState error={error} onRetry={handleRetry} />
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Policy Templates</h2>
          {meta && (
            <p className="text-sm text-gray-500 mt-1">
              {meta.total_items} template{meta.total_items !== 1 ? "s" : ""} available
            </p>
          )}
        </div>
        {loading && (
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            Loading...
          </div>
        )}
      </div>

      {/* Search and Filters */}
      <SearchFilters params={params} onParamsChange={handleParamsChange} />

      {/* Template Grid */}
      <div className="mt-6">
        {templates.length === 0 ? (
          <EmptyTemplatesState />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {templates.map((template) => (
              <TemplateCard
                key={template.id}
                template={template}
                onClick={onTemplateSelect}
              />
            ))}
          </div>
        )}
      </div>

      {/* Pagination */}
      {meta && <Pagination meta={meta} onPageChange={handlePageChange} />}
    </div>
  );
}

// Memoize to prevent re-renders when parent updates with same props
export const TemplateList = memo(TemplateListComponent);
