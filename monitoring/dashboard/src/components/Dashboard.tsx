/**
 * ACGS-2 Unified Monitoring Dashboard
 * Constitutional Hash: cdd01ef066bc6cf2
 *
 * Main dashboard component integrating all monitoring panels
 */

import { useState, useCallback } from "react";
import { HealthPanel } from "./HealthPanel";
import { MetricsChart } from "./MetricsChart";
import { AlertsList } from "./AlertsList";
import { ServiceGrid } from "./ServiceGrid";
import {
  useDashboardOverview,
  useMetrics,
  useAlerts,
  useServices,
  useWebSocket,
} from "../hooks/useDashboard";
import type { WebSocketMessage } from "../types/api";
import { CONSTITUTIONAL_HASH } from "../types/api";

export function Dashboard(): JSX.Element {
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Data hooks
  const { data: overview, loading: overviewLoading, refetch: refetchOverview } =
    useDashboardOverview();
  const { data: metrics, loading: metricsLoading, refetch: refetchMetrics } =
    useMetrics(30);
  const { data: alerts, loading: alertsLoading, refetch: refetchAlerts } =
    useAlerts();
  const { data: services, loading: servicesLoading, refetch: refetchServices } =
    useServices();

  // WebSocket for real-time updates
  const handleWebSocketMessage = useCallback((message: WebSocketMessage) => {
    setLastUpdate(new Date());
    // Handle real-time updates based on message type
    switch (message.type) {
      case "overview":
        // Trigger refetch to get fresh data
        refetchOverview();
        break;
      case "metrics":
        refetchMetrics();
        break;
      case "alert":
        refetchAlerts();
        break;
      case "health":
        refetchServices();
        break;
    }
  }, [refetchOverview, refetchMetrics, refetchAlerts, refetchServices]);

  const { connected } = useWebSocket(handleWebSocketMessage);

  const handleRefresh = () => {
    refetchOverview();
    refetchMetrics();
    refetchAlerts();
    refetchServices();
    setLastUpdate(new Date());
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <svg
                  className="w-8 h-8 text-blue-600"
                  fill="none"
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
                <div>
                  <h1 className="text-xl font-bold text-gray-900">
                    ACGS-2 Monitoring Dashboard
                  </h1>
                  <p className="text-xs text-gray-500">
                    Constitutional AI Governance System
                  </p>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-4">
              {/* Connection Status */}
              <div className="flex items-center gap-2">
                <span
                  className={`
                    w-2 h-2 rounded-full
                    ${connected ? "bg-green-500 animate-pulse" : "bg-red-500"}
                  `}
                />
                <span className="text-sm text-gray-600">
                  {connected ? "Live" : "Disconnected"}
                </span>
              </div>

              {/* Last Update */}
              <div className="text-sm text-gray-500">
                Updated: {lastUpdate.toLocaleTimeString()}
              </div>

              {/* Refresh Button */}
              <button
                onClick={handleRefresh}
                className="
                  inline-flex items-center gap-2 px-3 py-1.5
                  text-sm font-medium text-gray-700
                  bg-white border border-gray-300 rounded-md
                  hover:bg-gray-50 focus:outline-none focus:ring-2
                  focus:ring-blue-500 focus:ring-offset-2
                "
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
                Refresh
              </button>

              {/* Constitutional Hash Badge */}
              <div className="hidden lg:flex items-center gap-1 px-2 py-1 bg-green-100 text-green-800 rounded text-xs font-mono">
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                  />
                </svg>
                {CONSTITUTIONAL_HASH}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="space-y-6">
          {/* Health Overview */}
          <HealthPanel overview={overview} loading={overviewLoading} />

          {/* Metrics and Alerts Row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <MetricsChart metrics={metrics} loading={metricsLoading} />
            <AlertsList
              alerts={alerts}
              overview={overview}
              loading={alertsLoading}
            />
          </div>

          {/* Services Grid */}
          <ServiceGrid services={services} loading={servicesLoading} />
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between text-sm text-gray-500">
            <div>
              ACGS-2 Unified Monitoring Dashboard v1.0.0
            </div>
            <div className="flex items-center gap-4">
              <span>Constitutional Hash: {CONSTITUTIONAL_HASH}</span>
              <span>
                &copy; {new Date().getFullYear()} ACGS Team
              </span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
