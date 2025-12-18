/**
 * ACGS-2 Policy Service
 * Constitutional Hash: cdd01ef066bc6cf2
 */

import { ACGS2Client } from '../client';
import {
  CONSTITUTIONAL_HASH,
  Policy,
  PolicySchema,
  PolicyStatus,
  CreatePolicyRequest,
  UpdatePolicyRequest,
  PaginationParams,
  PaginatedResponse,
  ApiResponse,
} from '../types';
import { ValidationError } from '../utils';

// =============================================================================
// Policy Service
// =============================================================================

export class PolicyService {
  private readonly basePath = '/api/v1/policies';

  constructor(private readonly client: ACGS2Client) {}

  // ===========================================================================
  // CRUD Operations
  // ===========================================================================

  /**
   * Creates a new policy
   */
  async create(request: CreatePolicyRequest): Promise<Policy> {
    const response = await this.client.post<Policy>(this.basePath, {
      ...request,
      constitutionalHash: CONSTITUTIONAL_HASH,
    });

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to create policy');
    }

    return this.validatePolicy(response.data);
  }

  /**
   * Retrieves a policy by ID
   */
  async get(policyId: string): Promise<Policy> {
    const response = await this.client.get<Policy>(`${this.basePath}/${policyId}`);

    if (!response.success || !response.data) {
      throw new ValidationError(`Policy not found: ${policyId}`);
    }

    return this.validatePolicy(response.data);
  }

  /**
   * Updates a policy
   */
  async update(policyId: string, request: UpdatePolicyRequest): Promise<Policy> {
    const response = await this.client.patch<Policy>(`${this.basePath}/${policyId}`, request);

    if (!response.success || !response.data) {
      throw new ValidationError(`Failed to update policy: ${policyId}`);
    }

    return this.validatePolicy(response.data);
  }

  /**
   * Deletes a policy
   */
  async delete(policyId: string): Promise<void> {
    await this.client.delete(`${this.basePath}/${policyId}`);
  }

  /**
   * Lists policies with pagination
   */
  async list(params?: PaginationParams & {
    status?: PolicyStatus;
    tags?: string[];
  }): Promise<PaginatedResponse<Policy>> {
    const response = await this.client.get<PaginatedResponse<Policy>>(this.basePath, params);

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to list policies');
    }

    // Validate each policy
    response.data.data = response.data.data.map((policy) => this.validatePolicy(policy));
    return response.data;
  }

  // ===========================================================================
  // Status Management
  // ===========================================================================

  /**
   * Activates a policy
   */
  async activate(policyId: string): Promise<Policy> {
    return this.updateStatus(policyId, PolicyStatus.ACTIVE);
  }

  /**
   * Deprecates a policy
   */
  async deprecate(policyId: string): Promise<Policy> {
    return this.updateStatus(policyId, PolicyStatus.DEPRECATED);
  }

  /**
   * Archives a policy
   */
  async archive(policyId: string): Promise<Policy> {
    return this.updateStatus(policyId, PolicyStatus.ARCHIVED);
  }

  /**
   * Submits a policy for review
   */
  async submitForReview(policyId: string): Promise<Policy> {
    return this.updateStatus(policyId, PolicyStatus.PENDING_REVIEW);
  }

  /**
   * Approves a policy
   */
  async approve(policyId: string): Promise<Policy> {
    return this.updateStatus(policyId, PolicyStatus.APPROVED);
  }

  private async updateStatus(policyId: string, status: PolicyStatus): Promise<Policy> {
    const response = await this.client.post<Policy>(
      `${this.basePath}/${policyId}/status`,
      { status }
    );

    if (!response.success || !response.data) {
      throw new ValidationError(`Failed to update policy status: ${policyId}`);
    }

    return this.validatePolicy(response.data);
  }

  // ===========================================================================
  // Versioning
  // ===========================================================================

  /**
   * Gets all versions of a policy
   */
  async getVersions(policyId: string): Promise<Policy[]> {
    const response = await this.client.get<Policy[]>(`${this.basePath}/${policyId}/versions`);

    if (!response.success || !response.data) {
      throw new ValidationError(`Failed to get policy versions: ${policyId}`);
    }

    return response.data.map((policy) => this.validatePolicy(policy));
  }

  /**
   * Gets a specific version of a policy
   */
  async getVersion(policyId: string, version: string): Promise<Policy> {
    const response = await this.client.get<Policy>(
      `${this.basePath}/${policyId}/versions/${version}`
    );

    if (!response.success || !response.data) {
      throw new ValidationError(`Policy version not found: ${policyId}@${version}`);
    }

    return this.validatePolicy(response.data);
  }

  /**
   * Creates a new version of a policy
   */
  async createVersion(policyId: string, changes: UpdatePolicyRequest): Promise<Policy> {
    const response = await this.client.post<Policy>(
      `${this.basePath}/${policyId}/versions`,
      changes
    );

    if (!response.success || !response.data) {
      throw new ValidationError(`Failed to create policy version: ${policyId}`);
    }

    return this.validatePolicy(response.data);
  }

  // ===========================================================================
  // Validation & Analysis
  // ===========================================================================

  /**
   * Validates policy rules syntax
   */
  async validate(rules: Record<string, unknown>[]): Promise<{
    valid: boolean;
    errors: string[];
  }> {
    const response = await this.client.post<{ valid: boolean; errors: string[] }>(
      `${this.basePath}/validate`,
      { rules, constitutionalHash: CONSTITUTIONAL_HASH }
    );

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to validate policy rules');
    }

    return response.data;
  }

  /**
   * Analyzes policy impact
   */
  async analyzeImpact(policyId: string): Promise<{
    affectedAgents: string[];
    riskLevel: 'low' | 'medium' | 'high';
    estimatedImpact: string;
    recommendations: string[];
  }> {
    const response = await this.client.get<{
      affectedAgents: string[];
      riskLevel: 'low' | 'medium' | 'high';
      estimatedImpact: string;
      recommendations: string[];
    }>(`${this.basePath}/${policyId}/impact`);

    if (!response.success || !response.data) {
      throw new ValidationError(`Failed to analyze policy impact: ${policyId}`);
    }

    return response.data;
  }

  /**
   * Compares two policy versions
   */
  async diff(policyId: string, fromVersion: string, toVersion: string): Promise<{
    additions: Record<string, unknown>[];
    deletions: Record<string, unknown>[];
    modifications: Array<{
      path: string;
      from: unknown;
      to: unknown;
    }>;
  }> {
    const response = await this.client.get<{
      additions: Record<string, unknown>[];
      deletions: Record<string, unknown>[];
      modifications: Array<{ path: string; from: unknown; to: unknown }>;
    }>(`${this.basePath}/${policyId}/diff`, { fromVersion, toVersion });

    if (!response.success || !response.data) {
      throw new ValidationError(`Failed to diff policy versions: ${policyId}`);
    }

    return response.data;
  }

  // ===========================================================================
  // Helpers
  // ===========================================================================

  private validatePolicy(data: unknown): Policy {
    const result = PolicySchema.safeParse(data);
    if (!result.success) {
      throw new ValidationError('Invalid policy data', {
        validation: result.error.errors.map((e) => e.message),
      });
    }
    return result.data;
  }
}
