/**
 * MSW Request Handlers for Analytics API
 *
 * Defines mock responses for all analytics-api endpoints
 * used by the dashboard widgets during testing.
 */

import { http, HttpResponse } from "msw";

const API_BASE_URL = "http://localhost:8080";

/** Sample insight data */
const mockInsightData = {
  summary:
    "Governance compliance improved by 15% this week with reduced policy violations across all departments.",
  business_impact:
    "Lower violation rates indicate improved team awareness of governance policies, reducing potential compliance risks.",
  recommended_action:
    "Continue current training programs and consider extending to new team members.",
  confidence: 0.85,
  generated_at: new Date().toISOString(),
  model_used: "gpt-4o",
  cached: false,
};

/** Sample anomalies data */
const mockAnomaliesData = {
  analysis_timestamp: new Date().toISOString(),
  total_records_analyzed: 150,
  anomalies_detected: 3,
  contamination_rate: 0.1,
  model_trained: true,
  anomalies: [
    {
      anomaly_id: "anomaly-001",
      timestamp: new Date().toISOString(),
      severity_score: 0.85,
      severity_label: "critical" as const,
      affected_metrics: {
        violation_count: 45,
        user_count: 12,
        policy_changes: 3,
      },
      description: "Unusual spike in policy violations detected",
    },
    {
      anomaly_id: "anomaly-002",
      timestamp: new Date().toISOString(),
      severity_score: 0.65,
      severity_label: "medium" as const,
      affected_metrics: {
        violation_count: 22,
        user_count: 5,
      },
      description: "Moderate increase in access control violations",
    },
    {
      anomaly_id: "anomaly-003",
      timestamp: new Date().toISOString(),
      severity_score: 0.45,
      severity_label: "low" as const,
      affected_metrics: {
        violation_count: 8,
        user_count: 2,
      },
      description: "Minor anomaly in user activity patterns",
    },
  ],
};

/** Sample predictions data */
const mockPredictionsData = {
  forecast_timestamp: new Date().toISOString(),
  historical_days: 30,
  forecast_days: 30,
  model_trained: true,
  predictions: Array.from({ length: 30 }, (_, i) => {
    const date = new Date();
    date.setDate(date.getDate() + i + 1);
    const baseValue = 10 + Math.sin(i / 5) * 3;
    return {
      date: date.toISOString().split("T")[0],
      predicted_value: baseValue,
      lower_bound: baseValue - 2,
      upper_bound: baseValue + 2,
      trend: i < 15 ? 0.1 : -0.05,
    };
  }),
  summary: {
    status: "success",
    mean_predicted_violations: 10.5,
    max_predicted_violations: 13.2,
    min_predicted_violations: 7.8,
    total_predicted_violations: 315,
    trend_direction: "stable",
    reason: null,
  },
  error_message: null,
};

/** Sample query response */
const mockQueryResponse = {
  query: "Show violations this week",
  answer:
    "There were 23 policy violations this week, a 15% decrease from last week. The most common violation type was access control (12 incidents), followed by data handling (8 incidents).",
  data: {
    total_violations: 23,
    violation_types: ["access_control", "data_handling", "authentication"],
    top_policies: ["policy-auth-001", "policy-data-002"],
    trend: "decreasing",
  },
  query_understood: true,
  generated_at: new Date().toISOString(),
};

/** Sample compliance data */
const mockComplianceData = {
  analysis_timestamp: new Date().toISOString(),
  overall_score: 84.5,
  trend: "improving" as const,
  violations_by_severity: {
    critical: 2,
    high: 5,
    medium: 8,
    low: 12,
  },
  total_violations: 27,
  recent_violations: [
    {
      id: "comp-001",
      rule: "Sensitive data must be encrypted at rest",
      severity: "critical" as const,
      description: "Unencrypted PII detected in production database",
      timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
      framework: "SOC2",
      evidence: {
        database: "users_prod",
        field: "ssn",
        encryption_status: "none",
      },
    },
    {
      id: "comp-002",
      rule: "API access requires multi-factor authentication",
      severity: "high" as const,
      description: "Admin API endpoint accessible without MFA",
      timestamp: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
      framework: "HIPAA",
      evidence: {
        endpoint: "/admin/users",
        mfa_enabled: false,
      },
    },
    {
      id: "comp-003",
      rule: "Security patches must be applied within 30 days",
      severity: "medium" as const,
      description: "Critical security patch overdue by 12 days",
      timestamp: new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString(),
      framework: "PCI-DSS",
      evidence: {
        package: "openssl",
        current_version: "1.1.1k",
        required_version: "1.1.1w",
        days_overdue: 12,
      },
    },
    {
      id: "comp-004",
      rule: "Access logs must be retained for 90 days",
      severity: "low" as const,
      description: "Log retention policy set to 60 days",
      timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
      framework: "SOC2",
    },
    {
      id: "comp-005",
      rule: "Failed login attempts must trigger alerts",
      severity: "medium" as const,
      description: "Alert threshold set too high (50 attempts)",
      timestamp: new Date(Date.now() - 36 * 60 * 60 * 1000).toISOString(),
      framework: "HIPAA",
      evidence: {
        current_threshold: 50,
        recommended_threshold: 10,
      },
    },
  ],
  frameworks_analyzed: ["SOC2", "HIPAA", "PCI-DSS", "GDPR"],
};

/**
 * MSW handlers for all analytics API endpoints
 */
export const handlers = [
  // GET /insights
  http.get(`${API_BASE_URL}/insights`, () => {
    return HttpResponse.json(mockInsightData);
  }),

  // GET /insights/status
  http.get(`${API_BASE_URL}/insights/status`, () => {
    return HttpResponse.json({ status: "healthy", service: "insights" });
  }),

  // GET /anomalies
  http.get(`${API_BASE_URL}/anomalies`, ({ request }) => {
    const url = new URL(request.url);
    const severity = url.searchParams.get("severity");

    if (severity) {
      const filteredAnomalies = {
        ...mockAnomaliesData,
        anomalies: mockAnomaliesData.anomalies.filter(
          (a) => a.severity_label === severity
        ),
      };
      filteredAnomalies.anomalies_detected = filteredAnomalies.anomalies.length;
      return HttpResponse.json(filteredAnomalies);
    }

    return HttpResponse.json(mockAnomaliesData);
  }),

  // GET /anomalies/status
  http.get(`${API_BASE_URL}/anomalies/status`, () => {
    return HttpResponse.json({ status: "healthy", service: "anomalies" });
  }),

  // GET /predictions
  http.get(`${API_BASE_URL}/predictions`, () => {
    return HttpResponse.json(mockPredictionsData);
  }),

  // GET /predictions/status
  http.get(`${API_BASE_URL}/predictions/status`, () => {
    return HttpResponse.json({ status: "healthy", service: "predictions" });
  }),

  // GET /compliance
  http.get(`${API_BASE_URL}/compliance`, ({ request }) => {
    const url = new URL(request.url);
    const severity = url.searchParams.get("severity");

    if (severity) {
      const filteredViolations = {
        ...mockComplianceData,
        recent_violations: mockComplianceData.recent_violations.filter(
          (v) => v.severity === severity
        ),
      };
      return HttpResponse.json(filteredViolations);
    }

    return HttpResponse.json(mockComplianceData);
  }),

  // POST /query
  http.post(`${API_BASE_URL}/query`, async ({ request }) => {
    const body = await request.json();
    const question =
      typeof body === "object" && body !== null && "question" in body
        ? (body as { question: string }).question
        : "";

    return HttpResponse.json({
      ...mockQueryResponse,
      query: question,
    });
  }),

  // POST /export/pdf
  http.post(`${API_BASE_URL}/export/pdf`, () => {
    // Return a mock PDF blob
    const pdfContent = new Uint8Array([
      0x25, 0x50, 0x44, 0x46, // %PDF header
      0x2d, 0x31, 0x2e, 0x34, // -1.4
    ]);
    return new HttpResponse(pdfContent, {
      status: 200,
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition":
          'attachment; filename="governance_report.pdf"',
      },
    });
  }),

  // GET /export/status
  http.get(`${API_BASE_URL}/export/status`, () => {
    return HttpResponse.json({ status: "healthy", service: "export" });
  }),

  // Health check endpoint
  http.get(`${API_BASE_URL}/health`, () => {
    return HttpResponse.json({
      status: "healthy",
      version: "1.0.0",
      services: ["insights", "anomalies", "predictions", "query", "export"],
    });
  }),
];

/**
 * Error handlers for testing error states
 */
export const errorHandlers = {
  insightsError: http.get(`${API_BASE_URL}/insights`, () => {
    return HttpResponse.json(
      { detail: "Failed to generate insights" },
      { status: 500 }
    );
  }),

  anomaliesError: http.get(`${API_BASE_URL}/anomalies`, () => {
    return HttpResponse.json(
      { detail: "Anomaly detection service unavailable" },
      { status: 503 }
    );
  }),

  predictionsError: http.get(`${API_BASE_URL}/predictions`, () => {
    return HttpResponse.json(
      { detail: "Insufficient data for predictions" },
      { status: 400 }
    );
  }),

  complianceError: http.get(`${API_BASE_URL}/compliance`, () => {
    return HttpResponse.json(
      { detail: "Compliance service unavailable" },
      { status: 503 }
    );
  }),

  queryError: http.post(`${API_BASE_URL}/query`, () => {
    return HttpResponse.json(
      { detail: "Query processing failed" },
      { status: 500 }
    );
  }),

  networkError: http.get(`${API_BASE_URL}/insights`, () => {
    return HttpResponse.error();
  }),
};
