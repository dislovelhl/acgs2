/**
 * ACGS-2 Policy Registry Service
 * Constitutional Hash: cdd01ef066bc6cf2
 */

import { ACGS2Client } from '../client';
import {
  CONSTITUTIONAL_HASH,
  Policy,
  PolicyStatus,
  CreatePolicyRequest,
  UpdatePolicyRequest,
  PaginationParams,
  PaginatedResponse,
  ApiResponse,
} from '../types';
import { ValidationError } from '../utils';

// =============================================================================
// Types
// =============================================================================

export interface PolicyVersion {
  id: string;
  policyId: string;
  version: string;
  content: any;
  description?: string;
  createdAt: string;
  createdBy: string;
}

export interface PolicyBundle {
  id: string;
  name: string;
  description?: string;
  policies: string[];
  tenantId?: string;
  createdAt: string;
  updatedAt: string;
}

export interface CreateBundleRequest {
  name: string;
  policies: string[];
  description?: string;
}

export interface AuthRequest {
  username: string;
  password: string;
}

export interface AuthResponse {
  accessToken: string;
  tokenType: string;
  expiresIn: number;
  user: {
    id: string;
    username: string;
    roles: string[];
    tenantId?: string;
  };
}

export interface PolicyVerificationRequest {
  input: any;
}

export interface PolicyVerificationResponse {
  allowed: boolean;
  reason?: string;
  violations?: string[];
}

// =============================================================================
// Policy Registry Service
// =============================================================================

export class PolicyRegistryService {
  private readonly basePath = '/api/v1';

  constructor(private readonly client: ACGS2Client) {}

  // ===========================================================================
  // Policy CRUD Operations
  // ===========================================================================

  /**
   * List policies with optional filtering
   */
  async listPolicies(
    params?: {
      status?: PolicyStatus;
      limit?: number;
      offset?: number;
    }
  ): Promise<Policy[]> {
    const queryParams: any = {};
    if (params?.status) queryParams.status = params.status;
    if (params?.limit) queryParams.limit = params.limit;
    if (params?.offset) queryParams.offset = params.offset;

    const response = await this.client.get<Policy[]>(`${this.basePath}/policies`, { params: queryParams });

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to list policies');
    }

    return response.data.map(policy => this.validatePolicy(policy));
  }

  /**
   * Create a new policy
   */
  async createPolicy(request: CreatePolicyRequest): Promise<Policy> {
    const response = await this.client.post<Policy>(`${this.basePath}/policies`, {
      ...request,
      constitutionalHash: CONSTITUTIONAL_HASH,
    });

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to create policy');
    }

    return this.validatePolicy(response.data);
  }

  /**
   * Get a policy by ID
   */
  async getPolicy(policyId: string): Promise<Policy> {
    const response = await this.client.get<Policy>(`${this.basePath}/policies/${policyId}`);

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to get policy');
    }

    return this.validatePolicy(response.data);
  }

  /**
   * Update a policy
   */
  async updatePolicy(policyId: string, request: UpdatePolicyRequest): Promise<Policy> {
    const response = await this.client.patch<Policy>(`${this.basePath}/policies/${policyId}`, {
      ...request,
      constitutionalHash: CONSTITUTIONAL_HASH,
    });

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to update policy');
    }

    return this.validatePolicy(response.data);
  }

  /**
   * Activate a policy
   */
  async activatePolicy(policyId: string): Promise<Policy> {
    const response = await this.client.put<Policy>(`${this.basePath}/policies/${policyId}/activate`, {
      constitutionalHash: CONSTITUTIONAL_HASH,
    });

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to activate policy');
    }

    return this.validatePolicy(response.data);
  }

  /**
   * Verify input against a policy
   */
  async verifyPolicy(policyId: string, request: PolicyVerificationRequest): Promise<PolicyVerificationResponse> {
    const response = await this.client.post<PolicyVerificationResponse>(
      `${this.basePath}/policies/${policyId}/verify`,
      request
    );

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to verify policy');
    }

    return response.data;
  }

  /**
   * Get raw policy content
   */
  async getPolicyContent(policyId: string): Promise<any> {
    const response = await this.client.get<any>(`${this.basePath}/policies/${policyId}/content`);

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to get policy content');
    }

    return response.data;
  }

  // ===========================================================================
  // Policy Version Management
  // ===========================================================================

  /**
   * Get policy version history
   */
  async getPolicyVersions(policyId: string): Promise<PolicyVersion[]> {
    const response = await this.client.get<PolicyVersion[]>(`${this.basePath}/policies/${policyId}/versions`);

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to get policy versions');
    }

    return response.data;
  }

  /**
   * Create a new policy version
   */
  async createPolicyVersion(
    policyId: string,
    content: any,
    description?: string
  ): Promise<PolicyVersion> {
    const response = await this.client.post<PolicyVersion>(`${this.basePath}/policies/${policyId}/versions`, {
      content,
      description,
      constitutionalHash: CONSTITUTIONAL_HASH,
    });

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to create policy version');
    }

    return response.data;
  }

  /**
   * Get a specific policy version
   */
  async getPolicyVersion(policyId: string, version: string): Promise<PolicyVersion> {
    const response = await this.client.get<PolicyVersion>(
      `${this.basePath}/policies/${policyId}/versions/${version}`
    );

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to get policy version');
    }

    return response.data;
  }

  // ===========================================================================
  // Authentication
  // ===========================================================================

  /**
   * Authenticate and get access token
   */
  async authenticate(request: AuthRequest): Promise<AuthResponse> {
    const response = await this.client.post<AuthResponse>(`${this.basePath}/auth/token`, request);

    if (!response.success || !response.data) {
      throw new ValidationError('Authentication failed');
    }

    return response.data;
  }

  // ===========================================================================
  // Policy Bundles
  // ===========================================================================

  /**
   * List all policy bundles
   */
  async listBundles(): Promise<PolicyBundle[]> {
    const response = await this.client.get<PolicyBundle[]>(`${this.basePath}/bundles`);

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to list bundles');
    }

    return response.data;
  }

  /**
   * Create a policy bundle
   */
  async createBundle(request: CreateBundleRequest): Promise<PolicyBundle> {
    const response = await this.client.post<PolicyBundle>(`${this.basePath}/bundles`, {
      ...request,
      constitutionalHash: CONSTITUTIONAL_HASH,
    });

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to create bundle');
    }

    return response.data;
  }

  /**
   * Get a policy bundle by ID
   */
  async getBundle(bundleId: string): Promise<PolicyBundle> {
    const response = await this.client.get<PolicyBundle>(`${this.basePath}/bundles/${bundleId}`);

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to get bundle');
    }

    return response.data;
  }

  /**
   * Get the currently active policy bundle
   */
  async getActiveBundle(): Promise<PolicyBundle> {
    const response = await this.client.get<PolicyBundle>(`${this.basePath}/bundles/active`);

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to get active bundle');
    }

    return response.data;
  }

  // ===========================================================================
  // Health Checks
  // ===========================================================================

  /**
   * Check policy registry health
   */
  async healthCheck(): Promise<any> {
    const response = await this.client.get<any>(`${this.basePath}/health/policies`);

    if (!response.success || !response.data) {
      throw new ValidationError('Health check failed');
    }

    return response.data;
  }

  /**
   * Check cache health
   */
  async cacheHealth(): Promise<any> {
    const response = await this.client.get<any>(`${this.basePath}/health/cache`);

    if (!response.success || !response.data) {
      throw new ValidationError('Cache health check failed');
    }

    return response.data;
  }

  /**
   * Check connections health
   */
  async connectionsHealth(): Promise<any> {
    const response = await this.client.get<any>(`${this.basePath}/health/connections`);

    if (!response.success || !response.data) {
      throw new ValidationError('Connections health check failed');
    }

    return response.data;
  }

  // ===========================================================================
  // Helpers
  // ===========================================================================

  private validatePolicy(policy: any): Policy {
    // Basic validation - could be enhanced with Zod schemas
    if (!policy.id || !policy.name) {
      throw new ValidationError('Invalid policy data');
    }
    return policy as Policy;
  }
}
