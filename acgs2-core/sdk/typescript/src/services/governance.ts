/**
 * ACGS-2 Governance Service
 * Constitutional Hash: cdd01ef066bc6cf2
 */

import { ACGS2Client } from '../client';
import {
  CONSTITUTIONAL_HASH,
  GovernanceDecision,
  GovernanceDecisionSchema,
  ApprovalRequest,
  ApprovalRequestSchema,
  ApprovalStatus,
  CreateApprovalRequest,
  SubmitApprovalDecision,
  PaginationParams,
  PaginatedResponse,
} from '../types';
import { ValidationError, nowISO } from '../utils';

// =============================================================================
// Governance Types
// =============================================================================

export interface GovernancePolicy {
  id: string;
  name: string;
  description: string;
  type: 'constitutional' | 'operational' | 'ethical';
  priority: number;
  enabled: boolean;
  rules: GovernanceRule[];
  constitutionalHash: string;
}

export interface GovernanceRule {
  id: string;
  name: string;
  condition: string;
  action: 'allow' | 'deny' | 'require_approval';
  escalationLevel?: number;
  metadata?: Record<string, unknown>;
}

export interface EscalationPath {
  id: string;
  name: string;
  levels: Array<{
    level: number;
    approverRoles: string[];
    timeoutMinutes: number;
    autoEscalate: boolean;
  }>;
  constitutionalHash: string;
}

export interface GovernanceMetrics {
  totalDecisions: number;
  approvedCount: number;
  deniedCount: number;
  escalatedCount: number;
  averageDecisionTimeMs: number;
  complianceRate: number;
  byPolicy: Record<string, { decisions: number; complianceRate: number }>;
  constitutionalHash: string;
}

// =============================================================================
// Governance Service
// =============================================================================

export class GovernanceService {
  private readonly basePath = '/api/v1/governance';

  constructor(private readonly client: ACGS2Client) {}

  // ===========================================================================
  // Approval Requests
  // ===========================================================================

  /**
   * Creates an approval request
   */
  async createApprovalRequest(request: CreateApprovalRequest): Promise<ApprovalRequest> {
    const response = await this.client.post<ApprovalRequest>(`${this.basePath}/approvals`, {
      ...request,
      constitutionalHash: CONSTITUTIONAL_HASH,
    });

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to create approval request');
    }

    return this.validateApprovalRequest(response.data);
  }

  /**
   * Gets an approval request by ID
   */
  async getApprovalRequest(requestId: string): Promise<ApprovalRequest> {
    const response = await this.client.get<ApprovalRequest>(
      `${this.basePath}/approvals/${requestId}`
    );

    if (!response.success || !response.data) {
      throw new ValidationError(`Approval request not found: ${requestId}`);
    }

    return this.validateApprovalRequest(response.data);
  }

  /**
   * Lists approval requests
   */
  async listApprovalRequests(params?: PaginationParams & {
    status?: ApprovalStatus;
    requesterId?: string;
    pendingFor?: string; // Approver ID
  }): Promise<PaginatedResponse<ApprovalRequest>> {
    const response = await this.client.get<PaginatedResponse<ApprovalRequest>>(
      `${this.basePath}/approvals`,
      params
    );

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to list approval requests');
    }

    response.data.data = response.data.data.map((r) => this.validateApprovalRequest(r));
    return response.data;
  }

  /**
   * Submits an approval decision
   */
  async submitDecision(
    requestId: string,
    decision: SubmitApprovalDecision
  ): Promise<ApprovalRequest> {
    const response = await this.client.post<ApprovalRequest>(
      `${this.basePath}/approvals/${requestId}/decisions`,
      {
        ...decision,
        timestamp: nowISO(),
        constitutionalHash: CONSTITUTIONAL_HASH,
      }
    );

    if (!response.success || !response.data) {
      throw new ValidationError(`Failed to submit decision for request: ${requestId}`);
    }

    return this.validateApprovalRequest(response.data);
  }

  /**
   * Escalates an approval request
   */
  async escalate(requestId: string, reason: string): Promise<ApprovalRequest> {
    const response = await this.client.post<ApprovalRequest>(
      `${this.basePath}/approvals/${requestId}/escalate`,
      { reason }
    );

    if (!response.success || !response.data) {
      throw new ValidationError(`Failed to escalate request: ${requestId}`);
    }

    return this.validateApprovalRequest(response.data);
  }

  /**
   * Cancels an approval request
   */
  async cancelApprovalRequest(requestId: string, reason?: string): Promise<void> {
    await this.client.post(`${this.basePath}/approvals/${requestId}/cancel`, { reason });
  }

  // ===========================================================================
  // Governance Decisions
  // ===========================================================================

  /**
   * Gets a governance decision by ID
   */
  async getDecision(decisionId: string): Promise<GovernanceDecision> {
    const response = await this.client.get<GovernanceDecision>(
      `${this.basePath}/decisions/${decisionId}`
    );

    if (!response.success || !response.data) {
      throw new ValidationError(`Governance decision not found: ${decisionId}`);
    }

    return this.validateDecision(response.data);
  }

  /**
   * Lists governance decisions
   */
  async listDecisions(params?: PaginationParams & {
    decision?: 'approve' | 'deny' | 'escalate';
    requestId?: string;
    reviewerId?: string;
  }): Promise<PaginatedResponse<GovernanceDecision>> {
    const response = await this.client.get<PaginatedResponse<GovernanceDecision>>(
      `${this.basePath}/decisions`,
      params
    );

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to list governance decisions');
    }

    response.data.data = response.data.data.map((d) => this.validateDecision(d));
    return response.data;
  }

  /**
   * Verifies a governance decision's blockchain anchor
   */
  async verifyDecisionAnchor(decisionId: string): Promise<{
    verified: boolean;
    anchorDetails?: {
      transactionHash: string;
      blockNumber: number;
      timestamp: string;
    };
    constitutionalHash: string;
  }> {
    const response = await this.client.get<{
      verified: boolean;
      anchorDetails?: {
        transactionHash: string;
        blockNumber: number;
        timestamp: string;
      };
      constitutionalHash: string;
    }>(`${this.basePath}/decisions/${decisionId}/verify`);

    if (!response.success || !response.data) {
      throw new ValidationError(`Failed to verify decision anchor: ${decisionId}`);
    }

    return response.data;
  }

  // ===========================================================================
  // Governance Policies
  // ===========================================================================

  /**
   * Lists governance policies
   */
  async listPolicies(params?: PaginationParams & {
    type?: 'constitutional' | 'operational' | 'ethical';
    enabled?: boolean;
  }): Promise<PaginatedResponse<GovernancePolicy>> {
    const response = await this.client.get<PaginatedResponse<GovernancePolicy>>(
      `${this.basePath}/policies`,
      params
    );

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to list governance policies');
    }

    return response.data;
  }

  /**
   * Gets a governance policy by ID
   */
  async getPolicy(policyId: string): Promise<GovernancePolicy> {
    const response = await this.client.get<GovernancePolicy>(
      `${this.basePath}/policies/${policyId}`
    );

    if (!response.success || !response.data) {
      throw new ValidationError(`Governance policy not found: ${policyId}`);
    }

    return response.data;
  }

  // ===========================================================================
  // Escalation Paths
  // ===========================================================================

  /**
   * Lists escalation paths
   */
  async listEscalationPaths(): Promise<EscalationPath[]> {
    const response = await this.client.get<EscalationPath[]>(`${this.basePath}/escalation-paths`);

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to list escalation paths');
    }

    return response.data;
  }

  /**
   * Gets an escalation path by ID
   */
  async getEscalationPath(pathId: string): Promise<EscalationPath> {
    const response = await this.client.get<EscalationPath>(
      `${this.basePath}/escalation-paths/${pathId}`
    );

    if (!response.success || !response.data) {
      throw new ValidationError(`Escalation path not found: ${pathId}`);
    }

    return response.data;
  }

  // ===========================================================================
  // Constitutional Validation
  // ===========================================================================

  /**
   * Validates an action against constitutional principles
   */
  async validateConstitutional(params: {
    agentId: string;
    action: string;
    context: Record<string, unknown>;
    metadata?: Record<string, unknown>;
  }): Promise<{
    compliant: boolean;
    violations: Array<{
      principle: string;
      severity: 'warning' | 'violation' | 'critical';
      description: string;
    }>;
    recommendations: string[];
    requiresApproval: boolean;
    constitutionalHash: string;
  }> {
    const response = await this.client.post<{
      compliant: boolean;
      violations: Array<{
        principle: string;
        severity: 'warning' | 'violation' | 'critical';
        description: string;
      }>;
      recommendations: string[];
      requiresApproval: boolean;
      constitutionalHash: string;
    }>(`${this.basePath}/constitutional/validate`, {
      ...params,
      constitutionalHash: CONSTITUTIONAL_HASH,
    });

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to validate constitutional compliance');
    }

    return response.data;
  }

  /**
   * Gets constitutional principles
   */
  async getConstitutionalPrinciples(): Promise<Array<{
    id: string;
    name: string;
    description: string;
    category: string;
    priority: number;
    constitutionalHash: string;
  }>> {
    const response = await this.client.get<Array<{
      id: string;
      name: string;
      description: string;
      category: string;
      priority: number;
      constitutionalHash: string;
    }>>(`${this.basePath}/constitutional/principles`);

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to get constitutional principles');
    }

    return response.data;
  }

  // ===========================================================================
  // Metrics & Analytics
  // ===========================================================================

  /**
   * Gets governance metrics
   */
  async getMetrics(params?: {
    startDate?: string;
    endDate?: string;
    policyId?: string;
  }): Promise<GovernanceMetrics> {
    const response = await this.client.get<GovernanceMetrics>(
      `${this.basePath}/metrics`,
      params
    );

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to get governance metrics');
    }

    return response.data;
  }

  /**
   * Gets governance dashboard
   */
  async getDashboard(): Promise<{
    pendingApprovals: number;
    recentDecisions: GovernanceDecision[];
    complianceScore: number;
    activeAlerts: Array<{
      id: string;
      severity: 'low' | 'medium' | 'high' | 'critical';
      message: string;
      timestamp: string;
    }>;
    constitutionalHash: string;
  }> {
    const response = await this.client.get<{
      pendingApprovals: number;
      recentDecisions: GovernanceDecision[];
      complianceScore: number;
      activeAlerts: Array<{
        id: string;
        severity: 'low' | 'medium' | 'high' | 'critical';
        message: string;
        timestamp: string;
      }>;
      constitutionalHash: string;
    }>(`${this.basePath}/dashboard`);

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to get governance dashboard');
    }

    return response.data;
  }

  // ===========================================================================
  // Helpers
  // ===========================================================================

  private validateApprovalRequest(data: unknown): ApprovalRequest {
    const result = ApprovalRequestSchema.safeParse(data);
    if (!result.success) {
      throw new ValidationError('Invalid approval request data', {
        validation: result.error.errors.map((e) => e.message),
      });
    }
    return result.data;
  }

  private validateDecision(data: unknown): GovernanceDecision {
    const result = GovernanceDecisionSchema.safeParse(data);
    if (!result.success) {
      throw new ValidationError('Invalid governance decision data', {
        validation: result.error.errors.map((e) => e.message),
      });
    }
    return result.data;
  }
}
