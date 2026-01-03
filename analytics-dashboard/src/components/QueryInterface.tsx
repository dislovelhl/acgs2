/**
 * QueryInterface Component
 *
 * Natural language query interface for governance analytics.
 * Features:
 * - Text input for natural language questions
 * - Sample query suggestions
 * - Query result display with answer and data
 * - Loading, error, and success states
 * - Query history (recent queries)
 */

import { useCallback, useState, useRef, useEffect } from "react";
import {
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Clock,
  MessageSquare,
  Search,
  Send,
  Sparkles,
  X,
} from "lucide-react";

/** Query response data structure from the API */
interface QueryResponse {
  query: string;
  answer: string;
  data: Record<string, unknown>;
  query_understood: boolean;
  generated_at: string;
}

/** Query history item */
interface QueryHistoryItem {
  query: string;
  response: QueryResponse;
  timestamp: Date;
}

/** Widget loading state */
type LoadingState = "idle" | "loading" | "success" | "error";

/** API URL from environment */
const API_BASE_URL =
  import.meta.env.VITE_ANALYTICS_API_URL || "http://localhost:8080";

/** Maximum number of queries to keep in history */
const MAX_HISTORY_ITEMS = 5;

/** Sample queries to help users get started */
const SAMPLE_QUERIES = [
  "Show violations this week",
  "Which policy is violated most?",
  "What is the compliance trend?",
  "How many violations occurred yesterday?",
  "List critical security incidents",
];

/**
 * Formats a timestamp for display
 */
function formatTimestamp(date: Date): string {
  return date.toLocaleString(undefined, {
    dateStyle: "short",
    timeStyle: "short",
  });
}

/**
 * Formats data for display in a readable way
 */
function formatDataValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "N/A";
  }
  if (typeof value === "object") {
    return JSON.stringify(value, null, 2);
  }
  return String(value);
}

/**
 * QueryInterface - Natural language query component for governance data
 *
 * Features:
 * - Text input with submit button
 * - Sample query suggestions
 * - Query result display
 * - Recent query history
 * - Loading and error states
 */
export function QueryInterface(): JSX.Element {
  const [query, setQuery] = useState("");
  const [loadingState, setLoadingState] = useState<LoadingState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [currentResponse, setCurrentResponse] = useState<QueryResponse | null>(
    null
  );
  const [queryHistory, setQueryHistory] = useState<QueryHistoryItem[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [showSamples, setShowSamples] = useState(true);
  const inputRef = useRef<HTMLInputElement>(null);

  /**
   * Focus input on mount
   */
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);

  /**
   * Submits a query to the API
   */
  const submitQuery = useCallback(async (queryText: string) => {
    if (!queryText.trim()) {
      return;
    }

    setLoadingState("loading");
    setError(null);
    setShowSamples(false);

    try {
      const response = await fetch(`${API_BASE_URL}/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({ question: queryText }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || `Query failed: ${response.status}`
        );
      }

      const data: QueryResponse = await response.json();
      setCurrentResponse(data);
      setLoadingState("success");

      // Add to history
      setQueryHistory((prev) => {
        const newItem: QueryHistoryItem = {
          query: queryText,
          response: data,
          timestamp: new Date(),
        };
        const updated = [newItem, ...prev.slice(0, MAX_HISTORY_ITEMS - 1)];
        return updated;
      });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to process query";
      setError(message);
      setLoadingState("error");
    }
  }, []);

  /**
   * Handle form submission
   */
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    submitQuery(query);
  };

  /**
   * Handle sample query click
   */
  const handleSampleClick = (sampleQuery: string) => {
    setQuery(sampleQuery);
    submitQuery(sampleQuery);
  };

  /**
   * Handle history item click
   */
  const handleHistoryClick = (item: QueryHistoryItem) => {
    setQuery(item.query);
    setCurrentResponse(item.response);
    setLoadingState("success");
    setShowHistory(false);
  };

  /**
   * Clear current response and reset
   */
  const handleClear = () => {
    setQuery("");
    setCurrentResponse(null);
    setLoadingState("idle");
    setError(null);
    setShowSamples(true);
    inputRef.current?.focus();
  };

  return (
    <div className="rounded-lg bg-white p-6 shadow">
      {/* Header */}
      <div className="mb-4 flex items-center gap-2">
        <MessageSquare className="h-5 w-5 text-indigo-600" />
        <h2 className="text-lg font-semibold text-gray-900">
          Ask About Governance
        </h2>
        <Sparkles className="h-4 w-4 text-yellow-500" />
      </div>

      {/* Query Input Form */}
      <form onSubmit={handleSubmit} className="relative">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask a question about governance data..."
              className="w-full rounded-lg border border-gray-300 py-3 pl-10 pr-4 text-sm transition-colors focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              disabled={loadingState === "loading"}
              maxLength={500}
              aria-label="Query input"
            />
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            {query && loadingState !== "loading" && (
              <button
                type="button"
                onClick={handleClear}
                className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                title="Clear"
                aria-label="Clear query"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
          <button
            type="submit"
            disabled={!query.trim() || loadingState === "loading"}
            className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-3 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
            aria-label="Submit query"
          >
            {loadingState === "loading" ? (
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            <span className="hidden sm:inline">Ask</span>
          </button>
        </div>

        {/* History Toggle */}
        {queryHistory.length > 0 && (
          <button
            type="button"
            onClick={() => setShowHistory(!showHistory)}
            className="mt-2 flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
          >
            <Clock className="h-3 w-3" />
            Recent queries ({queryHistory.length})
            {showHistory ? (
              <ChevronUp className="h-3 w-3" />
            ) : (
              <ChevronDown className="h-3 w-3" />
            )}
          </button>
        )}
      </form>

      {/* Query History */}
      {showHistory && queryHistory.length > 0 && (
        <div className="mt-3 rounded-lg border border-gray-200 bg-gray-50 p-3">
          <div className="space-y-2">
            {queryHistory.map((item, index) => (
              <button
                key={index}
                onClick={() => handleHistoryClick(item)}
                className="block w-full rounded-md px-3 py-2 text-left text-sm text-gray-700 transition-colors hover:bg-gray-100"
              >
                <div className="flex items-center justify-between">
                  <span className="line-clamp-1">{item.query}</span>
                  <span className="ml-2 shrink-0 text-xs text-gray-400">
                    {formatTimestamp(item.timestamp)}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Sample Queries */}
      {showSamples && loadingState === "idle" && !currentResponse && (
        <div className="mt-4">
          <p className="mb-2 text-xs font-medium uppercase text-gray-500">
            Try asking:
          </p>
          <div className="flex flex-wrap gap-2">
            {SAMPLE_QUERIES.map((sample) => (
              <button
                key={sample}
                onClick={() => handleSampleClick(sample)}
                className="rounded-full border border-gray-200 bg-gray-50 px-3 py-1.5 text-xs text-gray-600 transition-colors hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700"
              >
                {sample}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Loading State */}
      {loadingState === "loading" && (
        <div className="mt-6 flex items-center justify-center py-8">
          <div className="text-center">
            <div className="mx-auto h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent"></div>
            <p className="mt-4 text-sm text-gray-500">
              Processing your query...
            </p>
          </div>
        </div>
      )}

      {/* Error State */}
      {loadingState === "error" && (
        <div className="mt-6 rounded-lg bg-red-50 p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 shrink-0 text-red-500" />
            <div>
              <p className="font-medium text-red-800">Query Failed</p>
              <p className="mt-1 text-sm text-red-600">{error}</p>
              <button
                onClick={() => submitQuery(query)}
                className="mt-3 rounded-md bg-red-100 px-3 py-1.5 text-sm font-medium text-red-700 transition-colors hover:bg-red-200"
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Query Results */}
      {loadingState === "success" && currentResponse && (
        <div className="mt-6 space-y-4">
          {/* Query Understood Indicator */}
          {!currentResponse.query_understood && (
            <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-3">
              <p className="text-sm text-yellow-700">
                Could not fully understand your query. Try rephrasing using
                keywords like &quot;violations&quot;, &quot;policies&quot;, or
                &quot;trends&quot;.
              </p>
            </div>
          )}

          {/* Answer Section */}
          <div className="rounded-lg bg-indigo-50 p-4">
            <div className="mb-2 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-indigo-600" />
              <span className="text-xs font-medium uppercase text-indigo-700">
                Answer
              </span>
            </div>
            <p className="text-sm leading-relaxed text-gray-700">
              {currentResponse.answer}
            </p>
          </div>

          {/* Data Section */}
          {Object.keys(currentResponse.data).length > 0 && (
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
              <div className="mb-2 flex items-center gap-2">
                <MessageSquare className="h-4 w-4 text-gray-600" />
                <span className="text-xs font-medium uppercase text-gray-600">
                  Related Data
                </span>
              </div>
              <div className="space-y-2">
                {Object.entries(currentResponse.data).map(([key, value]) => (
                  <div
                    key={key}
                    className="flex items-start justify-between gap-4 text-sm"
                  >
                    <span className="font-medium text-gray-600">
                      {key.replace(/_/g, " ")}:
                    </span>
                    <span className="text-right text-gray-800">
                      {Array.isArray(value) ? (
                        <span className="inline-flex flex-wrap justify-end gap-1">
                          {(value as unknown[]).map((item, i) => (
                            <span
                              key={i}
                              className="rounded-full bg-gray-200 px-2 py-0.5 text-xs"
                            >
                              {String(item)}
                            </span>
                          ))}
                        </span>
                      ) : (
                        formatDataValue(value)
                      )}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Metadata Footer */}
          <div className="flex items-center justify-between text-xs text-gray-400">
            <span>Query: &quot;{currentResponse.query}&quot;</span>
            {currentResponse.generated_at && (
              <span>
                Generated: {formatTimestamp(new Date(currentResponse.generated_at))}
              </span>
            )}
          </div>

          {/* Ask Another Button */}
          <button
            onClick={handleClear}
            className="w-full rounded-lg border border-gray-300 py-2 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-50"
          >
            Ask Another Question
          </button>
        </div>
      )}
    </div>
  );
}

export default QueryInterface;
