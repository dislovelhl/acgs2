/**
 * ACGS-2 Monitoring Dashboard API Types
 * Constitutional Hash: cdd01ef066bc6cf2
 *
 * TypeScript types matching the dashboard_api.py Pydantic models
 */

export const CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2";

// Enums matching Python counterparts
export type ServiceHealthStatus = "healthy" | "degraded" | "unhealthy" | "unknown";
export type AlertSeverity = "critical" | "error" | "warning" | "info";
export type CircuitBreakerState = "closed" | "open" | "half_open";

// Service Health
export interface ServiceHealth {
  name: string;
  status: ServiceHealthStatus;
  response_time_ms?: number;
  last_check: string; // ISO datetime
  error_message?: string;
  url?: string;
  constitutional_hash: string;
}

// System Metrics
export interface SystemMetrics {
  cpu_percent: number;
  memory_percent: number;
  memory_used_gb: number;
  memory_total_gb: number;
  disk_percent: number;
  disk_used_gb: number;
  disk_total_gb: number;
  network_bytes_sent: number;
  network_bytes_recv: number;
  process_count: number;
  timestamp: string;
}

// Performance Metrics
export interface PerformanceMetrics {
  p99_latency_ms: number;
  throughput_rps: number;
  cache_hit_rate: number;
  constitutional_compliance?: number;
  active_connections?: number;
  requests_total?: number;
  errors_total?: number;
  timestamp?: string;
}

// Circuit Breaker Status
export interface CircuitBreakerStatus {
  name: string;
  state: CircuitBreakerState;
  failure_count: number;
  success_count: number;
  last_failure_time?: string;
  recovery_timeout_ms?: number;
}

// Alert Info
export interface AlertInfo {
  alert_id: string;
  title: string;
  description: string;
  severity: AlertSeverity;
  source: string;
  status: string;
  timestamp: string;
  resolved_at?: string;
  metadata?: Record<string, unknown>;
  constitutional_hash: string;
}

// Dashboard Overview
export interface DashboardOverview {
  overall_status: ServiceHealthStatus;
  health_score: number;
  total_services: number;
  healthy_services: number;
  degraded_services: number;
  unhealthy_services: number;
  total_circuit_breakers: number;
  closed_breakers: number;
  open_breakers: number;
  half_open_breakers: number;
  p99_latency_ms: number;
  throughput_rps: number;
  cache_hit_rate: number;
  cpu_percent: number;
  memory_percent: number;
  disk_percent: number;
  critical_alerts: number;
  warning_alerts: number;
  total_alerts: number;
  timestamp: string;
  constitutional_hash: string;
}

// Health Aggregate Response
export interface HealthAggregateResponse {
  overall_status: ServiceHealthStatus;
  health_score: number;
  services: ServiceHealth[];
  circuit_breakers: CircuitBreakerStatus[];
  timestamp: string;
  constitutional_hash: string;
}

// Metrics Response
export interface MetricsResponse {
  system: SystemMetrics;
  performance: PerformanceMetrics;
  history: SystemMetrics[];
  timestamp: string;
  constitutional_hash: string;
}

// WebSocket Message
export interface WebSocketMessage {
  type: "overview" | "health" | "metrics" | "alert";
  data: DashboardOverview | HealthAggregateResponse | MetricsResponse | AlertInfo;
  timestamp: string;
  constitutional_hash: string;
}
