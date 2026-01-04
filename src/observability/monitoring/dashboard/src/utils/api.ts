import { getLogger } from '../../../../../sdk/typescript/src/utils/logger';
const logger = getLogger('api');


/**
 * ACGS-2 Monitoring Dashboard API Client
 * Constitutional Hash: cdd01ef066bc6cf2
 *
 * Utilities for connecting to the dashboard API
 */

import type {
  DashboardOverview,
  HealthAggregateResponse,
  MetricsResponse,
  AlertInfo,
  ServiceHealth,
  WebSocketMessage,
} from "../types/api";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8090";
const WS_BASE_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8090";

/**
 * Dashboard API client
 */
export class DashboardAPI {
  private baseUrl: string;
  private wsUrl: string;
  private ws: WebSocket | null = null;

  constructor(baseUrl: string = API_BASE_URL, wsUrl: string = WS_BASE_URL) {
    this.baseUrl = baseUrl;
    this.wsUrl = wsUrl;
  }

  /**
   * Fetch dashboard overview
   */
  async getOverview(): Promise<DashboardOverview> {
    const response = await fetch(`${this.baseUrl}/dashboard/overview`);
    if (!response.ok) {
      throw new Error(`Failed to fetch overview: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Fetch aggregated health status
   */
  async getHealth(): Promise<HealthAggregateResponse> {
    const response = await fetch(`${this.baseUrl}/dashboard/health`);
    if (!response.ok) {
      throw new Error(`Failed to fetch health: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Fetch system and performance metrics
   */
  async getMetrics(minutes?: number): Promise<MetricsResponse> {
    const url = minutes
      ? `${this.baseUrl}/dashboard/metrics?minutes=${minutes}`
      : `${this.baseUrl}/dashboard/metrics`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to fetch metrics: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Fetch active alerts
   */
  async getAlerts(severity?: string): Promise<AlertInfo[]> {
    const url = severity
      ? `${this.baseUrl}/dashboard/alerts?severity=${severity}`
      : `${this.baseUrl}/dashboard/alerts`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to fetch alerts: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Fetch service list with health status
   */
  async getServices(): Promise<ServiceHealth[]> {
    const response = await fetch(`${this.baseUrl}/dashboard/services`);
    if (!response.ok) {
      throw new Error(`Failed to fetch services: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Connect to WebSocket for real-time updates
   */
  connectWebSocket(
    onMessage: (message: WebSocketMessage) => void,
    onError?: (error: Event) => void,
    onClose?: (event: CloseEvent) => void
  ): void {
    if (this.ws) {
      this.ws.close();
    }

    this.ws = new WebSocket(`${this.wsUrl}/dashboard/ws`);

    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as WebSocketMessage;
        onMessage(message);
      } catch (error) {
        console.error("Failed to parse WebSocket message:", error);
      }
    };

    this.ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      logger.info("WebSocket closed:", event.code, event.reason;
    };

    this.ws.onclose = (event) => {
      console.log("WebSocket closed:", event.code, event.reason);
      onClose?.(event);
    };
  }

  /**
   * Disconnect WebSocket
   */
  disconnectWebSocket(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Check if WebSocket is connected
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}

// Default API instance
export const dashboardAPI = new DashboardAPI();
