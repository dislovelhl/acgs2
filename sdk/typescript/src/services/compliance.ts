/**
 * ACGS-2 Compliance Service
 * Constitutional Hash: cdd01ef066bc6cf2
 */

import { ACGS2Client } from '../client';
import {
  CONSTITUTIONAL_HASH,
  ComplianceResult,
  ComplianceResultSchema,
  ComplianceStatus,
  ValidateComplianceRequest,
  PaginationParams,
  PaginatedResponse,
} from '../types';
import { ValidationError } from '../utils';

// =============================================================================
// Compliance Types
// =============================================================================

export interface ComplianceReport {
  id: string;
  name: string;
  generatedAt: string;
  period: {
    start: string;
    end: string;
  };
  summary: {
    totalChecks: number;
    compliant: number;
    nonCompliant: number;
    pending: number;
    complianceRate: number;
  };
  results: ComplianceResult[];
  constitutionalHash: string;
}

export interface ComplianceRule {
  id: string;
  name: string;
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  category: string;
  enabled: boolean;
  constitutionalHash: string;
}

export interface ComplianceViolation {
  id: string;
  ruleId: string;
  ruleName: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  resource: string;
  resourceId: string;
  description: string;
  remediation: string;
  detectedAt: string;
  resolvedAt?: string;
  status: 'open' | 'acknowledged' | 'resolved' | 'false_positive';
  constitutionalHash: string;
}

// =============================================================================
// Compliance Service
// =============================================================================

export class ComplianceService {
  private readonly basePath = '/api/v1/compliance';

  constructor(private readonly client: ACGS2Client) {}

  // ===========================================================================
  // Validation
  // ===========================================================================

  /**
   * Validates compliance against a policy
   */
  async validate(request: ValidateComplianceRequest): Promise<ComplianceResult> {
    const response = await this.client.post<ComplianceResult>(`${this.basePath}/validate`, {
      ...request,
      constitutionalHash: CONSTITUTIONAL_HASH,
    });

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to validate compliance');
    }

    return this.validateResult(response.data);
  }

  /**
   * Validates compliance against multiple policies
   */
  async validateBatch(
    context: Record<string, unknown>,
    policyIds: string[]
  ): Promise<ComplianceResult[]> {
    const response = await this.client.post<ComplianceResult[]>(`${this.basePath}/validate/batch`, {
      context,
      policyIds,
      constitutionalHash: CONSTITUTIONAL_HASH,
    });

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to validate compliance batch');
    }

    return response.data.map((result) => this.validateResult(result));
  }

  /**
   * Validates an agent action against policies
   */
  async validateAction(
    agentId: string,
    action: string,
    context: Record<string, unknown>
  ): Promise<{
    allowed: boolean;
    results: ComplianceResult[];
    blockingViolations: string[];
  }> {
    const response = await this.client.post<{
      allowed: boolean;
      results: ComplianceResult[];
      blockingViolations: string[];
    }>(`${this.basePath}/validate/action`, {
      agentId,
      action,
      context,
      constitutionalHash: CONSTITUTIONAL_HASH,
    });

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to validate action');
    }

    return response.data;
  }

  // ===========================================================================
  // Results
  // ===========================================================================

  /**
   * Gets a compliance result by ID
   */
  async getResult(resultId: string): Promise<ComplianceResult> {
    const response = await this.client.get<ComplianceResult>(
      `${this.basePath}/results/${resultId}`
    );

    if (!response.success || !response.data) {
      throw new ValidationError(`Compliance result not found: ${resultId}`);
    }

    return this.validateResult(response.data);
  }

  /**
   * Lists compliance results
   */
  async listResults(params?: PaginationParams & {
    policyId?: string;
    status?: ComplianceStatus;
    startDate?: string;
    endDate?: string;
  }): Promise<PaginatedResponse<ComplianceResult>> {
    const response = await this.client.get<PaginatedResponse<ComplianceResult>>(
      `${this.basePath}/results`,
      params
    );

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to list compliance results');
    }

    response.data.data = response.data.data.map((result) => this.validateResult(result));
    return response.data;
  }

  // ===========================================================================
  // Reports
  // ===========================================================================

  /**
   * Generates a compliance report
   */
  async generateReport(options: {
    name: string;
    policyIds?: string[];
    startDate: string;
    endDate: string;
    format?: 'json' | 'pdf' | 'csv';
  }): Promise<ComplianceReport> {
    const response = await this.client.post<ComplianceReport>(`${this.basePath}/reports`, {
      ...options,
      constitutionalHash: CONSTITUTIONAL_HASH,
    });

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to generate compliance report');
    }

    return response.data;
  }

  /**
   * Gets a compliance report by ID
   */
  async getReport(reportId: string): Promise<ComplianceReport> {
    const response = await this.client.get<ComplianceReport>(
      `${this.basePath}/reports/${reportId}`
    );

    if (!response.success || !response.data) {
      throw new ValidationError(`Compliance report not found: ${reportId}`);
    }

    return response.data;
  }

  /**
   * Lists compliance reports
   */
  async listReports(params?: PaginationParams): Promise<PaginatedResponse<ComplianceReport>> {
    const response = await this.client.get<PaginatedResponse<ComplianceReport>>(
      `${this.basePath}/reports`,
      params
    );

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to list compliance reports');
    }

    return response.data;
  }

  /**
   * Downloads a report in specified format
   */
  async downloadReport(reportId: string, format: 'pdf' | 'csv'): Promise<Blob> {
    const response = await this.client.get<Blob>(
      `${this.basePath}/reports/${reportId}/download`,
      { format },
      { responseType: 'blob' }
    );

    if (!response.data) {
      throw new ValidationError(`Failed to download report: ${reportId}`);
    }

    return response.data;
  }

  // ===========================================================================
  // Rules
  // ===========================================================================

  /**
   * Lists compliance rules
   */
  async listRules(params?: PaginationParams & {
    category?: string;
    enabled?: boolean;
  }): Promise<PaginatedResponse<ComplianceRule>> {
    const response = await this.client.get<PaginatedResponse<ComplianceRule>>(
      `${this.basePath}/rules`,
      params
    );

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to list compliance rules');
    }

    return response.data;
  }

  /**
   * Gets a compliance rule by ID
   */
  async getRule(ruleId: string): Promise<ComplianceRule> {
    const response = await this.client.get<ComplianceRule>(`${this.basePath}/rules/${ruleId}`);

    if (!response.success || !response.data) {
      throw new ValidationError(`Compliance rule not found: ${ruleId}`);
    }

    return response.data;
  }

  /**
   * Enables a compliance rule
   */
  async enableRule(ruleId: string): Promise<ComplianceRule> {
    const response = await this.client.post<ComplianceRule>(
      `${this.basePath}/rules/${ruleId}/enable`
    );

    if (!response.success || !response.data) {
      throw new ValidationError(`Failed to enable rule: ${ruleId}`);
    }

    return response.data;
  }

  /**
   * Disables a compliance rule
   */
  async disableRule(ruleId: string): Promise<ComplianceRule> {
    const response = await this.client.post<ComplianceRule>(
      `${this.basePath}/rules/${ruleId}/disable`
    );

    if (!response.success || !response.data) {
      throw new ValidationError(`Failed to disable rule: ${ruleId}`);
    }

    return response.data;
  }

  // ===========================================================================
  // Violations
  // ===========================================================================

  /**
   * Lists compliance violations
   */
  async listViolations(params?: PaginationParams & {
    status?: 'open' | 'acknowledged' | 'resolved' | 'false_positive';
    severity?: 'low' | 'medium' | 'high' | 'critical';
    ruleId?: string;
  }): Promise<PaginatedResponse<ComplianceViolation>> {
    const response = await this.client.get<PaginatedResponse<ComplianceViolation>>(
      `${this.basePath}/violations`,
      params
    );

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to list violations');
    }

    return response.data;
  }

  /**
   * Gets a violation by ID
   */
  async getViolation(violationId: string): Promise<ComplianceViolation> {
    const response = await this.client.get<ComplianceViolation>(
      `${this.basePath}/violations/${violationId}`
    );

    if (!response.success || !response.data) {
      throw new ValidationError(`Violation not found: ${violationId}`);
    }

    return response.data;
  }

  /**
   * Acknowledges a violation
   */
  async acknowledgeViolation(
    violationId: string,
    notes?: string
  ): Promise<ComplianceViolation> {
    const response = await this.client.post<ComplianceViolation>(
      `${this.basePath}/violations/${violationId}/acknowledge`,
      { notes }
    );

    if (!response.success || !response.data) {
      throw new ValidationError(`Failed to acknowledge violation: ${violationId}`);
    }

    return response.data;
  }

  /**
   * Resolves a violation
   */
  async resolveViolation(
    violationId: string,
    resolution: string
  ): Promise<ComplianceViolation> {
    const response = await this.client.post<ComplianceViolation>(
      `${this.basePath}/violations/${violationId}/resolve`,
      { resolution }
    );

    if (!response.success || !response.data) {
      throw new ValidationError(`Failed to resolve violation: ${violationId}`);
    }

    return response.data;
  }

  /**
   * Marks a violation as false positive
   */
  async markFalsePositive(
    violationId: string,
    justification: string
  ): Promise<ComplianceViolation> {
    const response = await this.client.post<ComplianceViolation>(
      `${this.basePath}/violations/${violationId}/false-positive`,
      { justification }
    );

    if (!response.success || !response.data) {
      throw new ValidationError(`Failed to mark false positive: ${violationId}`);
    }

    return response.data;
  }

  // ===========================================================================
  // Dashboard & Statistics
  // ===========================================================================

  /**
   * Gets compliance dashboard data
   */
  async getDashboard(): Promise<{
    overallScore: number;
    trend: 'improving' | 'stable' | 'declining';
    byCategory: Record<string, { score: number; violations: number }>;
    bySeverity: Record<string, number>;
    recentViolations: ComplianceViolation[];
    constitutionalHash: string;
  }> {
    const response = await this.client.get<{
      overallScore: number;
      trend: 'improving' | 'stable' | 'declining';
      byCategory: Record<string, { score: number; violations: number }>;
      bySeverity: Record<string, number>;
      recentViolations: ComplianceViolation[];
      constitutionalHash: string;
    }>(`${this.basePath}/dashboard`);

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to get compliance dashboard');
    }

    return response.data;
  }

  // ===========================================================================
  // Helpers
  // ===========================================================================

  private validateResult(data: unknown): ComplianceResult {
    const result = ComplianceResultSchema.safeParse(data);
    if (!result.success) {
      throw new ValidationError('Invalid compliance result data', {
        validation: result.error.errors.map((e) => e.message),
      });
    }
    return result.data;
  }
}
