/**
 * ACGS-2 Template Detail Component
 * Constitutional Hash: 018-policy-marketplace
 *
 * Displays detailed information about a policy template with version history.
 * Optimized with React.memo and useMemo for performance.
 */

import { memo, useMemo, useState, useCallback, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { marketplaceAPI, ApiError } from "@services/api";
import type {
  TemplateResponse,
  VersionListItem,
  TemplateCategory,
  TemplateFormat,
  RatingCreate,
} from "@types/template";

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

const formatExtensions: Record<TemplateFormat, string> = {
  json: ".json",
  yaml: ".yaml",
  rego: ".rego",
} as const;

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

const formatDateTime = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

// ====================
// Loading Skeleton
// ====================

const TemplateDetailSkeleton = memo(function TemplateDetailSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      {/* Header skeleton */}
      <div className="flex items-start justify-between">
        <div className="space-y-3 flex-1">
          <div className="h-8 w-1/2 bg-gray-200 rounded" />
          <div className="h-4 w-3/4 bg-gray-200 rounded" />
        </div>
        <div className="flex gap-2">
          <div className="h-10 w-24 bg-gray-200 rounded" />
          <div className="h-10 w-32 bg-gray-200 rounded" />
        </div>
      </div>

      {/* Tags skeleton */}
      <div className="flex gap-2">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-6 w-20 bg-gray-200 rounded" />
        ))}
      </div>

      {/* Stats skeleton */}
      <div className="grid grid-cols-4 gap-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-20 bg-gray-200 rounded-lg" />
        ))}
      </div>

      {/* Content skeleton */}
      <div className="h-64 bg-gray-200 rounded-lg" />
    </div>
  );
});

// ====================
// Error State
// ====================

interface ErrorStateProps {
  error: string;
  onRetry: () => void;
  onBack: () => void;
}

const ErrorState = memo(function ErrorState({
  error,
  onRetry,
  onBack,
}: ErrorStateProps) {
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
      <p className="text-lg font-medium text-gray-900">Failed to load template</p>
      <p className="text-sm text-red-600 mt-1">{error}</p>
      <div className="flex justify-center gap-3 mt-4">
        <button
          onClick={onBack}
          className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition-colors"
        >
          Go Back
        </button>
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        >
          Try Again
        </button>
      </div>
    </div>
  );
});

// ====================
// Stat Card
// ====================

interface StatCardProps {
  label: string;
  value: string | number;
  icon: React.ReactNode;
}

const StatCard = memo(function StatCard({ label, value, icon }: StatCardProps) {
  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <div className="flex items-center gap-2 text-gray-500 text-sm mb-1">
        {icon}
        <span>{label}</span>
      </div>
      <div className="text-xl font-semibold text-gray-900">{value}</div>
    </div>
  );
});

// ====================
// Version Dropdown
// ====================

interface VersionDropdownProps {
  versions: VersionListItem[];
  selectedVersion: string;
  onVersionChange: (version: string) => void;
  loading?: boolean;
}

const VersionDropdown = memo(function VersionDropdown({
  versions,
  selectedVersion,
  onVersionChange,
  loading,
}: VersionDropdownProps) {
  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      onVersionChange(e.target.value);
    },
    [onVersionChange]
  );

  return (
    <div className="flex items-center gap-2">
      <label className="text-sm font-medium text-gray-700">Version:</label>
      <select
        value={selectedVersion}
        onChange={handleChange}
        disabled={loading}
        className="
          px-3 py-1.5 border border-gray-300 rounded-md text-sm
          focus:ring-2 focus:ring-blue-500 focus:border-blue-500
          disabled:opacity-50 disabled:cursor-not-allowed
        "
      >
        {versions.map((v) => (
          <option key={v.id} value={v.version}>
            v{v.version} - {formatDate(v.created_at)}
          </option>
        ))}
      </select>
      {loading && (
        <svg className="w-4 h-4 animate-spin text-gray-500" fill="none" viewBox="0 0 24 24">
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
      )}
    </div>
  );
});

// ====================
// Rating Component
// ====================

interface RatingStarsProps {
  rating: number | null;
  ratingCount: number;
  onRate?: (rating: number) => void;
  interactive?: boolean;
}

const RatingStars = memo(function RatingStars({
  rating,
  ratingCount,
  onRate,
  interactive = false,
}: RatingStarsProps) {
  const [hoverRating, setHoverRating] = useState<number | null>(null);

  const displayRating = hoverRating ?? rating ?? 0;

  const handleClick = useCallback(
    (star: number) => {
      if (interactive && onRate) {
        onRate(star);
      }
    },
    [interactive, onRate]
  );

  return (
    <div className="flex items-center gap-2">
      <div className="flex items-center">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            disabled={!interactive}
            onClick={() => handleClick(star)}
            onMouseEnter={() => interactive && setHoverRating(star)}
            onMouseLeave={() => setHoverRating(null)}
            className={`
              ${interactive ? "cursor-pointer hover:scale-110" : "cursor-default"}
              transition-transform
            `}
          >
            <svg
              className={`w-5 h-5 ${
                star <= displayRating ? "text-yellow-400" : "text-gray-300"
              }`}
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
            </svg>
          </button>
        ))}
      </div>
      {rating !== null && (
        <span className="text-sm text-gray-600">
          {rating.toFixed(1)} ({ratingCount} {ratingCount === 1 ? "rating" : "ratings"})
        </span>
      )}
      {rating === null && (
        <span className="text-sm text-gray-500">No ratings yet</span>
      )}
    </div>
  );
});

// ====================
// Version History Panel
// ====================

interface VersionHistoryProps {
  versions: VersionListItem[];
  selectedVersion: string;
  onVersionSelect: (version: string) => void;
}

const VersionHistory = memo(function VersionHistory({
  versions,
  selectedVersion,
  onVersionSelect,
}: VersionHistoryProps) {
  return (
    <div className="border border-gray-200 rounded-lg">
      <div className="px-4 py-3 bg-gray-50 border-b border-gray-200 rounded-t-lg">
        <h3 className="font-medium text-gray-900">Version History</h3>
      </div>
      <div className="divide-y divide-gray-100 max-h-64 overflow-y-auto">
        {versions.map((version) => (
          <button
            key={version.id}
            onClick={() => onVersionSelect(version.version)}
            className={`
              w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors
              ${selectedVersion === version.version ? "bg-blue-50" : ""}
            `}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="font-medium text-gray-900">v{version.version}</span>
                {selectedVersion === version.version && (
                  <span className="px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-800 rounded">
                    Current
                  </span>
                )}
              </div>
              <span className="text-sm text-gray-500">
                {formatDateTime(version.created_at)}
              </span>
            </div>
            {version.changelog && (
              <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                {version.changelog}
              </p>
            )}
            {version.created_by && (
              <p className="text-xs text-gray-400 mt-1">by {version.created_by}</p>
            )}
          </button>
        ))}
      </div>
    </div>
  );
});

// ====================
// Main Component
// ====================

function TemplateDetailComponent(): JSX.Element {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  // State
  const [template, setTemplate] = useState<TemplateResponse | null>(null);
  const [versions, setVersions] = useState<VersionListItem[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [versionsLoading, setVersionsLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ratingSubmitting, setRatingSubmitting] = useState(false);

  // Parse template ID
  const templateId = useMemo(() => {
    const parsed = parseInt(id || "", 10);
    return isNaN(parsed) ? null : parsed;
  }, [id]);

  // Fetch template details
  const fetchTemplate = useCallback(async () => {
    if (templateId === null) {
      setError("Invalid template ID");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const [templateData, versionsData] = await Promise.all([
        marketplaceAPI.getTemplate(templateId),
        marketplaceAPI.listVersions(templateId),
      ]);

      setTemplate(templateData);
      setVersions(versionsData.items);
      setSelectedVersion(templateData.current_version);

      // Track view event
      try {
        await marketplaceAPI.trackEvent(templateId, { event_type: "view" });
      } catch {
        // Silently ignore analytics errors
      }
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
  }, [templateId]);

  // Load template on mount
  useEffect(() => {
    fetchTemplate();
  }, [fetchTemplate]);

  // Handle version change
  const handleVersionChange = useCallback(
    async (version: string) => {
      if (templateId === null) return;

      setVersionsLoading(true);
      setSelectedVersion(version);

      try {
        // Find the version to get its content
        const versionItem = versions.find((v) => v.version === version);
        if (versionItem && template) {
          // For now, just update the selected version
          // In a full implementation, we would fetch the version content
          setSelectedVersion(version);
        }
      } finally {
        setVersionsLoading(false);
      }
    },
    [templateId, versions, template]
  );

  // Handle download
  const handleDownload = useCallback(async () => {
    if (templateId === null || !template) return;

    setDownloading(true);

    try {
      const blob = await marketplaceAPI.downloadTemplate(templateId);
      const extension = formatExtensions[template.format];
      const filename = `${template.name.replace(/[^a-z0-9]/gi, "-").toLowerCase()}-v${selectedVersion}${extension}`;

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      // Update download count in UI
      setTemplate((prev) =>
        prev ? { ...prev, downloads: prev.downloads + 1 } : prev
      );
    } catch (err) {
      if (err instanceof ApiError) {
        alert(`Download failed: ${err.detail || err.message}`);
      } else {
        alert("Download failed. Please try again.");
      }
    } finally {
      setDownloading(false);
    }
  }, [templateId, template, selectedVersion]);

  // Handle rating
  const handleRate = useCallback(
    async (rating: number) => {
      if (templateId === null) return;

      setRatingSubmitting(true);

      try {
        const ratingData: RatingCreate = { rating };
        await marketplaceAPI.rateTemplate(templateId, ratingData);

        // Refresh template to get updated rating
        const updatedTemplate = await marketplaceAPI.getTemplate(templateId);
        setTemplate(updatedTemplate);
      } catch (err) {
        if (err instanceof ApiError) {
          alert(`Rating failed: ${err.detail || err.message}`);
        } else {
          alert("Rating failed. Please try again.");
        }
      } finally {
        setRatingSubmitting(false);
      }
    },
    [templateId]
  );

  // Handle back navigation
  const handleBack = useCallback(() => {
    navigate("/templates");
  }, [navigate]);

  // Handle retry
  const handleRetry = useCallback(() => {
    fetchTemplate();
  }, [fetchTemplate]);

  // Memoized formatted values
  const formattedCreatedAt = useMemo(
    () => (template ? formatDateTime(template.created_at) : ""),
    [template]
  );

  const formattedUpdatedAt = useMemo(
    () => (template ? formatDateTime(template.updated_at) : ""),
    [template]
  );

  // Render loading state
  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
        <TemplateDetailSkeleton />
      </div>
    );
  }

  // Render error state
  if (error || !template) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
        <ErrorState
          error={error || "Template not found"}
          onRetry={handleRetry}
          onBack={handleBack}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back button */}
      <button
        onClick={handleBack}
        className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M10 19l-7-7m0 0l7-7m-7 7h18"
          />
        </svg>
        Back to templates
      </button>

      {/* Main content card */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 mb-6">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-2xl font-bold text-gray-900">{template.name}</h1>
              {template.is_verified && (
                <span
                  className="flex-shrink-0 flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded"
                  title="Verified Template"
                >
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                      clipRule="evenodd"
                    />
                  </svg>
                  Verified
                </span>
              )}
            </div>
            <p className="text-gray-600">{template.description}</p>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3">
            <VersionDropdown
              versions={versions}
              selectedVersion={selectedVersion}
              onVersionChange={handleVersionChange}
              loading={versionsLoading}
            />
            <button
              onClick={handleDownload}
              disabled={downloading}
              className="
                flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md
                hover:bg-blue-700 transition-colors
                disabled:opacity-50 disabled:cursor-not-allowed
              "
            >
              {downloading ? (
                <>
                  <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
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
                  Downloading...
                </>
              ) : (
                <>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                    />
                  </svg>
                  Download
                </>
              )}
            </button>
          </div>
        </div>

        {/* Tags */}
        <div className="flex flex-wrap gap-2 mb-6">
          <span
            className={`px-3 py-1 text-sm font-medium rounded ${categoryStyles[template.category]}`}
          >
            {categoryLabels[template.category]}
          </span>
          <span className="px-3 py-1 text-sm font-medium rounded bg-gray-100 text-gray-700">
            {formatLabels[template.format]}
          </span>
          <span className="px-3 py-1 text-sm font-medium rounded bg-gray-100 text-gray-700">
            v{selectedVersion}
          </span>
          {template.is_public ? (
            <span className="px-3 py-1 text-sm font-medium rounded bg-green-100 text-green-800">
              Public
            </span>
          ) : (
            <span className="px-3 py-1 text-sm font-medium rounded bg-orange-100 text-orange-800">
              Private
            </span>
          )}
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <StatCard
            label="Downloads"
            value={template.downloads.toLocaleString()}
            icon={
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                />
              </svg>
            }
          />
          <StatCard
            label="Rating"
            value={
              template.rating !== null
                ? `${template.rating.toFixed(1)} / 5`
                : "No ratings"
            }
            icon={
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
            }
          />
          <StatCard
            label="Created"
            value={formattedCreatedAt}
            icon={
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                />
              </svg>
            }
          />
          <StatCard
            label="Updated"
            value={formattedUpdatedAt}
            icon={
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
            }
          />
        </div>

        {/* Author Info */}
        {template.author_name && (
          <div className="flex items-center gap-2 mb-6 text-sm text-gray-600">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
              />
            </svg>
            <span>Created by {template.author_name}</span>
          </div>
        )}

        {/* Rating Section */}
        <div className="mb-6">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Rate this template:</h3>
          <RatingStars
            rating={template.rating}
            ratingCount={template.rating_count}
            onRate={handleRate}
            interactive={!ratingSubmitting}
          />
          {ratingSubmitting && (
            <p className="text-sm text-gray-500 mt-2">Submitting rating...</p>
          )}
        </div>

        {/* Template Content Preview */}
        <div className="mb-6">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Template Content:</h3>
          <div className="bg-gray-900 rounded-lg p-4 overflow-auto max-h-96">
            <pre className="text-sm text-gray-100 font-mono whitespace-pre-wrap">
              {template.content}
            </pre>
          </div>
        </div>
      </div>

      {/* Version History Card */}
      {versions.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
          <VersionHistory
            versions={versions}
            selectedVersion={selectedVersion}
            onVersionSelect={handleVersionChange}
          />
        </div>
      )}
    </div>
  );
}

// Memoize to prevent re-renders when parent updates with same props
export const TemplateDetail = memo(TemplateDetailComponent);
