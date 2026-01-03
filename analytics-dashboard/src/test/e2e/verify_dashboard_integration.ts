import { getLogger } from '../../../../../../sdk/typescript/src/utils/logger';
import { API_BASE_URL } from '../../lib';

const logger = getLogger('verify_dashboard_integration');


/**
 * Dashboard → Analytics-API Integration Verification Script
 *
 * This script provides programmatic verification of the dashboard's
 * integration with the analytics-api backend.
 *
 * Run with: npx tsx src/test/e2e/verify_dashboard_integration.ts
 *
 * Prerequisites:
 * - analytics-api running at http://localhost:8080
 * - analytics-dashboard running at http://localhost:5173
 */

interface VerificationResult {
  endpoint: string;
  status: "pass" | "fail";
  message: string;
  duration: number;
  response?: unknown;
}

interface VerificationReport {
  timestamp: string;
  total_checks: number;
  passed: number;
  failed: number;
  results: VerificationResult[];
}

/**
 * Verifies a single API endpoint
 */
async function verifyEndpoint(
  endpoint: string,
  method: "GET" | "POST" = "GET",
  body?: object
): Promise<VerificationResult> {
  const start = Date.now();
  const url = `${API_BASE_URL}${endpoint}`;

  try {
    const options: RequestInit = {
      method,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
    };

    if (body && method === "POST") {
      options.body = JSON.stringify(body);
    }

    const response = await fetch(url, options);
    const duration = Date.now() - start;

    if (!response.ok) {
      return {
        endpoint,
        status: "fail",
        message: `HTTP ${response.status}: ${response.statusText}`,
        duration,
      };
    }

    const contentType = response.headers.get("content-type");
    let data: unknown;

    if (contentType?.includes("application/json")) {
      data = await response.json();
    } else if (contentType?.includes("application/pdf")) {
      const blob = await response.blob();
      data = { type: "pdf", size: blob.size };
    } else {
      data = await response.text();
    }

    return {
      endpoint,
      status: "pass",
      message: `Success (${duration}ms)`,
      duration,
      response: data,
    };
  } catch (error) {
    const duration = Date.now() - start;
    return {
      endpoint,
      status: "fail",
      message: error instanceof Error ? error.message : "Unknown error",
      duration,
    };
  }
}

/**
 * Verifies the /insights endpoint
 */
async function verifyInsightsEndpoint(): Promise<VerificationResult> {
  const result = await verifyEndpoint("/insights");

  if (result.status === "pass" && result.response) {
    const data = result.response as Record<string, unknown>;

    // Verify required fields
    const requiredFields = [
      "summary",
      "business_impact",
      "recommended_action",
      "confidence",
    ];
    const missingFields = requiredFields.filter(
      (field) => !(field in data)
    );

    if (missingFields.length > 0) {
      return {
        ...result,
        status: "fail",
        message: `Missing required fields: ${missingFields.join(", ")}`,
      };
    }

    // Verify confidence is in valid range
    const confidence = data.confidence as number;
    if (confidence < 0 || confidence > 1) {
      return {
        ...result,
        status: "fail",
        message: `Invalid confidence value: ${confidence}`,
      };
    }
  }

  return result;
}

/**
 * Verifies the /anomalies endpoint
 */
async function verifyAnomaliesEndpoint(): Promise<VerificationResult> {
  const result = await verifyEndpoint("/anomalies");

  if (result.status === "pass" && result.response) {
    const data = result.response as Record<string, unknown>;

    // Verify required fields
    const requiredFields = [
      "analysis_timestamp",
      "total_records_analyzed",
      "anomalies_detected",
      "anomalies",
    ];
    const missingFields = requiredFields.filter(
      (field) => !(field in data)
    );

    if (missingFields.length > 0) {
      return {
        ...result,
        status: "fail",
        message: `Missing required fields: ${missingFields.join(", ")}`,
      };
    }

    // Verify anomalies is an array
    if (!Array.isArray(data.anomalies)) {
      return {
        ...result,
        status: "fail",
        message: "anomalies field is not an array",
      };
    }

    // Verify each anomaly has required structure
    const anomalies = data.anomalies as Array<Record<string, unknown>>;
    for (const anomaly of anomalies) {
      if (!anomaly.anomaly_id || !anomaly.severity_label) {
        return {
          ...result,
          status: "fail",
          message: "Anomaly missing required fields (anomaly_id, severity_label)",
        };
      }
    }
  }

  return result;
}

/**
 * Verifies the /predictions endpoint
 */
async function verifyPredictionsEndpoint(): Promise<VerificationResult> {
  const result = await verifyEndpoint("/predictions");

  if (result.status === "pass" && result.response) {
    const data = result.response as Record<string, unknown>;

    // Verify required fields
    const requiredFields = [
      "forecast_timestamp",
      "forecast_days",
      "model_trained",
      "predictions",
      "summary",
    ];
    const missingFields = requiredFields.filter(
      (field) => !(field in data)
    );

    if (missingFields.length > 0) {
      return {
        ...result,
        status: "fail",
        message: `Missing required fields: ${missingFields.join(", ")}`,
      };
    }

    // Verify predictions is an array
    if (!Array.isArray(data.predictions)) {
      return {
        ...result,
        status: "fail",
        message: "predictions field is not an array",
      };
    }
  }

  return result;
}

/**
 * Verifies the /query endpoint
 */
async function verifyQueryEndpoint(): Promise<VerificationResult> {
  const result = await verifyEndpoint("/query", "POST", {
    question: "Show violations this week",
  });

  if (result.status === "pass" && result.response) {
    const data = result.response as Record<string, unknown>;

    // Verify required fields
    const requiredFields = ["query", "answer", "data", "query_understood"];
    const missingFields = requiredFields.filter(
      (field) => !(field in data)
    );

    if (missingFields.length > 0) {
      return {
        ...result,
        status: "fail",
        message: `Missing required fields: ${missingFields.join(", ")}`,
      };
    }

    // Verify answer is not empty
    if (!data.answer || (data.answer as string).length === 0) {
      return {
        ...result,
        status: "fail",
        message: "Empty answer returned",
      };
    }
  }

  return result;
}

/**
 * Verifies the /export/pdf endpoint
 */
async function verifyExportPdfEndpoint(): Promise<VerificationResult> {
  const start = Date.now();
  const url = `${API_BASE_URL}/export/pdf`;

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Accept: "application/pdf",
      },
    });
    const duration = Date.now() - start;

    if (!response.ok) {
      return {
        endpoint: "/export/pdf",
        status: "fail",
        message: `HTTP ${response.status}: ${response.statusText}`,
        duration,
      };
    }

    const contentType = response.headers.get("content-type");
    const contentDisposition = response.headers.get("content-disposition");

    // Verify PDF content type
    if (!contentType?.includes("application/pdf")) {
      return {
        endpoint: "/export/pdf",
        status: "fail",
        message: `Wrong content type: ${contentType}`,
        duration,
      };
    }

    // Verify PDF file download
    const blob = await response.blob();
    if (blob.size < 100) {
      return {
        endpoint: "/export/pdf",
        status: "fail",
        message: `PDF too small (${blob.size} bytes)`,
        duration,
      };
    }

    // Verify content-disposition header
    if (!contentDisposition?.includes("attachment")) {
      return {
        endpoint: "/export/pdf",
        status: "fail",
        message: "Missing attachment content-disposition",
        duration,
      };
    }

    return {
      endpoint: "/export/pdf",
      status: "pass",
      message: `Success - PDF size: ${blob.size} bytes (${duration}ms)`,
      duration,
      response: { size: blob.size, contentType, contentDisposition },
    };
  } catch (error) {
    const duration = Date.now() - start;
    return {
      endpoint: "/export/pdf",
      status: "fail",
      message: error instanceof Error ? error.message : "Unknown error",
      duration,
    };
  }
}

  logger.info("=" .repeat(60);
  logger.info("Dashboard → Analytics-API Integration Verification";
  logger.info("=" .repeat(60);
  logger.info(`API Base URL: ${API_BASE_URL}`;
  logger.info(`Timestamp: ${new Date().toISOString()}`;
  logger.info("";
  console.log("=" .repeat(60));
  console.log(`API Base URL: ${API_BASE_URL}`);
  console.log(`Timestamp: ${new Date().toISOString()}`);
  console.log("");
  logger.info("1. Verifying GET /insights endpoint...";
  const results: VerificationResult[] = [];
  logger.info(`   ${results[results.length - 1].status.toUpperCase()}: ${results[results.length - 1].message}`;
  // Verify each endpoint
  logger.info("2. Verifying GET /anomalies endpoint...";
  results.push(await verifyInsightsEndpoint());
  logger.info(`   ${results[results.length - 1].status.toUpperCase()}: ${results[results.length - 1].message}`;

  logger.info("3. Verifying GET /predictions endpoint...";
  results.push(await verifyAnomaliesEndpoint());
  logger.info(`   ${results[results.length - 1].status.toUpperCase()}: ${results[results.length - 1].message}`;

  logger.info("4. Verifying POST /query endpoint...";
  results.push(await verifyPredictionsEndpoint());
  logger.info(`   ${results[results.length - 1].status.toUpperCase()}: ${results[results.length - 1].message}`;

  logger.info("5. Verifying POST /export/pdf endpoint...";
  results.push(await verifyQueryEndpoint());
  logger.info(`   ${results[results.length - 1].status.toUpperCase()}: ${results[results.length - 1].message}`;

  console.log("5. Verifying POST /export/pdf endpoint...");
  results.push(await verifyExportPdfEndpoint());
  console.log(`   ${results[results.length - 1].status.toUpperCase()}: ${results[results.length - 1].message}`);

  logger.info("";
  logger.info("=" .repeat(60);
  logger.info("VERIFICATION SUMMARY";
  logger.info("=" .repeat(60);
  logger.info(`Total Checks: ${results.length}`;
  logger.info(`Passed: ${passed}`;
  logger.info(`Failed: ${failed}`;
  logger.info(`Status: ${failed === 0 ? "ALL CHECKS PASSED" : "SOME CHECKS FAILED"}`;
  console.log(`Total Checks: ${results.length}`);
  console.log(`Passed: ${passed}`);
    logger.info("";
    logger.info("Failed checks:";

  if (failed > 0) {
    console.log("");
        logger.info(`  - ${r.endpoint}: ${r.message}`;
    results
      .filter((r) => r.status === "fail")
      .forEach((r) => {
        console.log(`  - ${r.endpoint}: ${r.message}`);
      });
  }

  return {
    timestamp: new Date().toISOString(),
    total_checks: results.length,
    passed,
    failed,
    results,
  };
}

// Run verification if executed directly
runVerification()
  .then((report) => {
    process.exit(report.failed > 0 ? 1 : 0);
  })
  .catch((error) => {
    console.error("Verification failed:", error);
    process.exit(1);
  });
