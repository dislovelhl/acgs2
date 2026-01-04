/**
 * Anomaly Detection Type Definitions
 *
 * Type definitions for anomaly detection data structures used across
 * the analytics dashboard for detecting unusual patterns in governance metrics.
 */

/**
 * Anomaly data structure from the API
 *
 * Represents a single detected anomaly with severity scoring,
 * affected metrics, and descriptive information.
 */
export interface AnomalyItem {
  /** Unique identifier for the anomaly */
  anomaly_id: string;

  /** ISO timestamp when the anomaly was detected */
  timestamp: string;

  /** Severity score as a decimal between 0 and 1 */
  severity_score: number;

  /** Human-readable severity classification */
  severity_label: "critical" | "high" | "medium" | "low";

  /** Metrics that were affected by this anomaly with their values */
  affected_metrics: Record<string, number | string>;

  /** Detailed description of the anomaly */
  description: string;
}

/**
 * Anomalies response from the API
 *
 * Contains the complete response from the anomaly detection endpoint
 * including analysis metadata and detected anomalies.
 */
export interface AnomaliesResponse {
  /** ISO timestamp when the analysis was performed */
  analysis_timestamp: string;

  /** Total number of records that were analyzed */
  total_records_analyzed: number;

  /** Count of anomalies detected in the analysis */
  anomalies_detected: number;

  /** Contamination rate used by the anomaly detection model */
  contamination_rate: number;

  /** Array of detected anomalies */
  anomalies: AnomalyItem[];

  /** Whether the anomaly detection model has been trained */
  model_trained: boolean;
}
