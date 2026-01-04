/**
 * ACGS-2 Monitoring Dashboard Hooks
 * Constitutional Hash: cdd01ef066bc6cf2
 *
 * React hooks for dashboard data fetching and WebSocket subscriptions
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { dashboardAPI } from "../utils/api";
import type {
  DashboardOverview,
  HealthAggregateResponse,
  MetricsResponse,
  AlertInfo,
  ServiceHealth,
  WebSocketMessage,
} from "../types/api";

// Polling interval in milliseconds
const POLL_INTERVAL = 5000;

interface UseDataResult<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

/**
 * Hook for fetching dashboard overview
 */
export function useDashboardOverview(): UseDataResult<DashboardOverview> {
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetch = useCallback(async () => {
    try {
      setLoading(true);
      const overview = await dashboardAPI.getOverview();
      setData(overview);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Unknown error"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
    const interval = setInterval(fetch, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [fetch]);

  return { data, loading, error, refetch: fetch };
}

/**
 * Hook for fetching health status
 */
export function useHealthStatus(): UseDataResult<HealthAggregateResponse> {
  const [data, setData] = useState<HealthAggregateResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetch = useCallback(async () => {
    try {
      setLoading(true);
      const health = await dashboardAPI.getHealth();
      setData(health);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Unknown error"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
    const interval = setInterval(fetch, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [fetch]);

  return { data, loading, error, refetch: fetch };
}

/**
 * Hook for fetching metrics
 */
export function useMetrics(historyMinutes?: number): UseDataResult<MetricsResponse> {
  const [data, setData] = useState<MetricsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetch = useCallback(async () => {
    try {
      setLoading(true);
      const metrics = await dashboardAPI.getMetrics(historyMinutes);
      setData(metrics);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Unknown error"));
    } finally {
      setLoading(false);
    }
  }, [historyMinutes]);

  useEffect(() => {
    fetch();
    const interval = setInterval(fetch, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [fetch]);

  return { data, loading, error, refetch: fetch };
}

/**
 * Hook for fetching alerts
 */
export function useAlerts(severity?: string): UseDataResult<AlertInfo[]> {
  const [data, setData] = useState<AlertInfo[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetch = useCallback(async () => {
    try {
      setLoading(true);
      const alerts = await dashboardAPI.getAlerts(severity);
      setData(alerts);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Unknown error"));
    } finally {
      setLoading(false);
    }
  }, [severity]);

  useEffect(() => {
    fetch();
    const interval = setInterval(fetch, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [fetch]);

  return { data, loading, error, refetch: fetch };
}

/**
 * Hook for fetching services
 */
export function useServices(): UseDataResult<ServiceHealth[]> {
  const [data, setData] = useState<ServiceHealth[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetch = useCallback(async () => {
    try {
      setLoading(true);
      const services = await dashboardAPI.getServices();
      setData(services);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Unknown error"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
    const interval = setInterval(fetch, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [fetch]);

  return { data, loading, error, refetch: fetch };
}

/**
 * Hook for WebSocket real-time updates
 */
export function useWebSocket(
  onMessage: (message: WebSocketMessage) => void
): { connected: boolean; reconnect: () => void } {
  const [connected, setConnected] = useState(false);
  const reconnectTimeoutRef = useRef<number | null>(null);

  const connect = useCallback(() => {
    dashboardAPI.connectWebSocket(
      (message) => {
        onMessage(message);
      },
      () => {
        setConnected(false);
        // Auto-reconnect after 5 seconds
        if (reconnectTimeoutRef.current === null) {
          reconnectTimeoutRef.current = window.setTimeout(() => {
            reconnectTimeoutRef.current = null;
            connect();
          }, 5000);
        }
      },
      () => {
        setConnected(false);
      }
    );
    setConnected(true);
  }, [onMessage]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current !== null) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      dashboardAPI.disconnectWebSocket();
    };
  }, [connect]);

  return { connected, reconnect: connect };
}
