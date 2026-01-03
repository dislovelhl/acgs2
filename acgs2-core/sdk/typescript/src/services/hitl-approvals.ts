/**
 * ACGS-2 HITL Approvals Service
 * Human-in-the-Loop approval workflows
 * Constitutional Hash: cdd01ef066bc6cf2
 */

import type { ACGS2Client } from '../client/index.js';
import { CONSTITUTIONAL_HASH } from '../types/index.js';
import type {
  ApprovalRequest,
  CreateApprovalRequest,
  PaginatedResponse,
  SubmitApprovalDecision,
} from '../types/index.js';

export class HITLApprovalsService {
  private client: ACGS2Client;
  private basePath = '/api/v1/hitl-approvals';

  constructor(client: ACGS2Client) {
    this.client = client;
  }

  async createApprovalRequest(request: CreateApprovalRequest): Promise<ApprovalRequest> {
    const response = await this.client.post(`${this.basePath}/approvals`, {
      ...request,
      constitutionalHash: CONSTITUTIONAL_HASH,
    });
    return response.data as ApprovalRequest;
  }

  async getApprovalRequest(requestId: string): Promise<ApprovalRequest> {
    const response = await this.client.get(`${this.basePath}/approvals/${requestId}`);
    return response.data as ApprovalRequest;
  }

  async listApprovalRequests(params?: {
    page?: number;
    pageSize?: number;
    status?: string;
    requesterId?: string;
    pendingFor?: string;
  }): Promise<PaginatedResponse<ApprovalRequest>> {
    const queryParams = new URLSearchParams();
    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.pageSize) queryParams.append('pageSize', params.pageSize.toString());
    if (params?.status) queryParams.append('status', params.status);
    if (params?.requesterId) queryParams.append('requesterId', params.requesterId);
    if (params?.pendingFor) queryParams.append('pendingFor', params.pendingFor);

    const response = await this.client.get(
      `${this.basePath}/approvals?${queryParams.toString()}`
    );
    return response.data as PaginatedResponse<ApprovalRequest>;
  }

  async submitDecision(
    requestId: string,
    decision: SubmitApprovalDecision
  ): Promise<ApprovalRequest> {
    const response = await this.client.post(`${this.basePath}/approvals/${requestId}/decisions`, {
      ...decision,
      timestamp: new Date().toISOString(),
      constitutionalHash: CONSTITUTIONAL_HASH,
    });
    return response.data as ApprovalRequest;
  }

  async escalateApprovalRequest(requestId: string, reason: string): Promise<ApprovalRequest> {
    const response = await this.client.post(`${this.basePath}/approvals/${requestId}/escalate`, {
      reason,
    });
    return response.data as ApprovalRequest;
  }

  async cancelApprovalRequest(requestId: string, reason?: string): Promise<void> {
    await this.client.post(`${this.basePath}/approvals/${requestId}/cancel`, {
      reason,
    });
  }

  async getPendingApprovals(
    userId: string,
    params?: { page?: number; pageSize?: number }
  ): Promise<PaginatedResponse<ApprovalRequest>> {
    const queryParams = new URLSearchParams();
    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.pageSize) queryParams.append('pageSize', params.pageSize.toString());

    const response = await this.client.get(
      `${this.basePath}/approvals/pending/${userId}?${queryParams.toString()}`
    );
    return response.data as PaginatedResponse<ApprovalRequest>;
  }

  async getApprovalWorkflowConfig(): Promise<Record<string, unknown>> {
    const response = await this.client.get(`${this.basePath}/config`);
    return response.data as Record<string, unknown>;
  }

  async updateApprovalWorkflowConfig(config: Record<string, unknown>): Promise<Record<string, unknown>> {
    const response = await this.client.put(`${this.basePath}/config`, {
      config,
      constitutionalHash: CONSTITUTIONAL_HASH,
    });
    return response.data as Record<string, unknown>;
  }

  async getApprovalMetrics(params?: {
    startDate?: string;
    endDate?: string;
  }): Promise<Record<string, unknown>> {
    const queryParams = new URLSearchParams();
    if (params?.startDate) queryParams.append('startDate', params.startDate);
    if (params?.endDate) queryParams.append('endDate', params.endDate);

    const response = await this.client.get(
      `${this.basePath}/metrics?${queryParams.toString()}`
    );
    return response.data as Record<string, unknown>;
  }
}
