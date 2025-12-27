/**
 * ACGS-2 Audit Service
 * Constitutional Hash: cdd01ef066bc6cf2
 */

import { ACGS2Client } from '../client';
import {
  CONSTITUTIONAL_HASH,
  AuditEvent,
  AuditEventSchema,
  EventCategory,
  EventSeverity,
  QueryAuditEventsRequest,
  PaginatedResponse,
} from '../types';
import { ValidationError, nowISO, generateUUID } from '../utils';

// =============================================================================
// Audit Types
// =============================================================================

export interface CreateAuditEventRequest {
  category: EventCategory;
  severity: EventSeverity;
  action: string;
  actor: string;
  resource: string;
  resourceId?: string;
  outcome: 'success' | 'failure' | 'partial';
  details?: Record<string, unknown>;
  correlationId?: string;
}

export interface AuditTrail {
  id: string;
  resourceType: string;
  resourceId: string;
  events: AuditEvent[];
  firstEvent: string;
  lastEvent: string;
  constitutionalHash: string;
}

export interface AuditExport {
  id: string;
  format: 'json' | 'csv' | 'parquet';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  query: QueryAuditEventsRequest;
  createdAt: string;
  completedAt?: string;
  downloadUrl?: string;
  recordCount?: number;
  constitutionalHash: string;
}

export interface AuditStatistics {
  totalEvents: number;
  byCategory: Record<string, number>;
  bySeverity: Record<string, number>;
  byOutcome: Record<string, number>;
  topActors: Array<{ actor: string; count: number }>;
  topResources: Array<{ resource: string; count: number }>;
  eventsOverTime: Array<{ timestamp: string; count: number }>;
  constitutionalHash: string;
}

// =============================================================================
// Audit Service
// =============================================================================

export class AuditService {
  private readonly basePath = '/api/v1/audit';

  constructor(private readonly client: ACGS2Client) {}

  // ===========================================================================
  // Event Management
  // ===========================================================================

  /**
   * Records an audit event
   */
  async record(event: CreateAuditEventRequest): Promise<AuditEvent> {
    const response = await this.client.post<AuditEvent>(`${this.basePath}/events`, {
      ...event,
      timestamp: nowISO(),
      constitutionalHash: CONSTITUTIONAL_HASH,
    });

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to record audit event');
    }

    return this.validateEvent(response.data);
  }

  /**
   * Records multiple audit events in batch
   */
  async recordBatch(events: CreateAuditEventRequest[]): Promise<AuditEvent[]> {
    const preparedEvents = events.map((event) => ({
      ...event,
      timestamp: nowISO(),
      constitutionalHash: CONSTITUTIONAL_HASH,
    }));

    const response = await this.client.post<AuditEvent[]>(
      `${this.basePath}/events/batch`,
      { events: preparedEvents }
    );

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to record audit events batch');
    }

    return response.data.map((e) => this.validateEvent(e));
  }

  /**
   * Gets an audit event by ID
   */
  async getEvent(eventId: string): Promise<AuditEvent> {
    const response = await this.client.get<AuditEvent>(`${this.basePath}/events/${eventId}`);

    if (!response.success || !response.data) {
      throw new ValidationError(`Audit event not found: ${eventId}`);
    }

    return this.validateEvent(response.data);
  }

  /**
   * Queries audit events with filters
   */
  async queryEvents(params: QueryAuditEventsRequest): Promise<PaginatedResponse<AuditEvent>> {
    const response = await this.client.get<PaginatedResponse<AuditEvent>>(
      `${this.basePath}/events`,
      params as Record<string, unknown>
    );

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to query audit events');
    }

    response.data.data = response.data.data.map((e) => this.validateEvent(e));
    return response.data;
  }

  /**
   * Searches audit events with full-text search
   */
  async searchEvents(
    query: string,
    params?: QueryAuditEventsRequest
  ): Promise<PaginatedResponse<AuditEvent>> {
    const response = await this.client.get<PaginatedResponse<AuditEvent>>(
      `${this.basePath}/events/search`,
      { query, ...params } as Record<string, unknown>
    );

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to search audit events');
    }

    response.data.data = response.data.data.map((e) => this.validateEvent(e));
    return response.data;
  }

  // ===========================================================================
  // Audit Trails
  // ===========================================================================

  /**
   * Gets the audit trail for a resource
   */
  async getTrail(resourceType: string, resourceId: string): Promise<AuditTrail> {
    const response = await this.client.get<AuditTrail>(
      `${this.basePath}/trails/${resourceType}/${resourceId}`
    );

    if (!response.success || !response.data) {
      throw new ValidationError(`Audit trail not found: ${resourceType}/${resourceId}`);
    }

    return response.data;
  }

  /**
   * Gets audit trails for multiple resources
   */
  async getTrailsBatch(
    resources: Array<{ resourceType: string; resourceId: string }>
  ): Promise<AuditTrail[]> {
    const response = await this.client.post<AuditTrail[]>(`${this.basePath}/trails/batch`, {
      resources,
    });

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to get audit trails batch');
    }

    return response.data;
  }

  // ===========================================================================
  // Export
  // ===========================================================================

  /**
   * Creates an export job for audit events
   */
  async createExport(options: {
    format: 'json' | 'csv' | 'parquet';
    query?: QueryAuditEventsRequest;
  }): Promise<AuditExport> {
    const response = await this.client.post<AuditExport>(`${this.basePath}/exports`, {
      ...options,
      constitutionalHash: CONSTITUTIONAL_HASH,
    });

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to create audit export');
    }

    return response.data;
  }

  /**
   * Gets an export job status
   */
  async getExport(exportId: string): Promise<AuditExport> {
    const response = await this.client.get<AuditExport>(`${this.basePath}/exports/${exportId}`);

    if (!response.success || !response.data) {
      throw new ValidationError(`Audit export not found: ${exportId}`);
    }

    return response.data;
  }

  /**
   * Lists export jobs
   */
  async listExports(): Promise<AuditExport[]> {
    const response = await this.client.get<AuditExport[]>(`${this.basePath}/exports`);

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to list audit exports');
    }

    return response.data;
  }

  /**
   * Waits for an export to complete
   */
  async waitForExport(
    exportId: string,
    options?: { timeoutMs?: number; pollIntervalMs?: number }
  ): Promise<AuditExport> {
    const timeout = options?.timeoutMs ?? 300000; // 5 minutes default
    const pollInterval = options?.pollIntervalMs ?? 5000; // 5 seconds default
    const startTime = Date.now();

    while (Date.now() - startTime < timeout) {
      const exportJob = await this.getExport(exportId);

      if (exportJob.status === 'completed') {
        return exportJob;
      }

      if (exportJob.status === 'failed') {
        throw new ValidationError(`Export job failed: ${exportId}`);
      }

      await new Promise((resolve) => setTimeout(resolve, pollInterval));
    }

    throw new ValidationError(`Export job timed out: ${exportId}`);
  }

  // ===========================================================================
  // Statistics & Analytics
  // ===========================================================================

  /**
   * Gets audit statistics
   */
  async getStatistics(params?: {
    startDate?: string;
    endDate?: string;
    category?: EventCategory;
  }): Promise<AuditStatistics> {
    const response = await this.client.get<AuditStatistics>(
      `${this.basePath}/statistics`,
      params
    );

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to get audit statistics');
    }

    return response.data;
  }

  /**
   * Gets activity summary for an actor
   */
  async getActorActivity(
    actor: string,
    params?: { startDate?: string; endDate?: string }
  ): Promise<{
    actor: string;
    totalEvents: number;
    byCategory: Record<string, number>;
    byOutcome: Record<string, number>;
    recentEvents: AuditEvent[];
    constitutionalHash: string;
  }> {
    const response = await this.client.get<{
      actor: string;
      totalEvents: number;
      byCategory: Record<string, number>;
      byOutcome: Record<string, number>;
      recentEvents: AuditEvent[];
      constitutionalHash: string;
    }>(`${this.basePath}/actors/${encodeURIComponent(actor)}/activity`, params);

    if (!response.success || !response.data) {
      throw new ValidationError(`Failed to get actor activity: ${actor}`);
    }

    return response.data;
  }

  /**
   * Gets activity summary for a resource
   */
  async getResourceActivity(
    resource: string,
    resourceId: string,
    params?: { startDate?: string; endDate?: string }
  ): Promise<{
    resource: string;
    resourceId: string;
    totalEvents: number;
    byAction: Record<string, number>;
    byActor: Record<string, number>;
    timeline: AuditEvent[];
    constitutionalHash: string;
  }> {
    const response = await this.client.get<{
      resource: string;
      resourceId: string;
      totalEvents: number;
      byAction: Record<string, number>;
      byActor: Record<string, number>;
      timeline: AuditEvent[];
      constitutionalHash: string;
    }>(`${this.basePath}/resources/${resource}/${resourceId}/activity`, params);

    if (!response.success || !response.data) {
      throw new ValidationError(`Failed to get resource activity: ${resource}/${resourceId}`);
    }

    return response.data;
  }

  // ===========================================================================
  // Retention & Archival
  // ===========================================================================

  /**
   * Gets retention policy
   */
  async getRetentionPolicy(): Promise<{
    defaultRetentionDays: number;
    byCategory: Record<string, number>;
    archiveEnabled: boolean;
    archiveDestination?: string;
    constitutionalHash: string;
  }> {
    const response = await this.client.get<{
      defaultRetentionDays: number;
      byCategory: Record<string, number>;
      archiveEnabled: boolean;
      archiveDestination?: string;
      constitutionalHash: string;
    }>(`${this.basePath}/retention`);

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to get retention policy');
    }

    return response.data;
  }

  // ===========================================================================
  // Integrity Verification
  // ===========================================================================

  /**
   * Verifies the integrity of audit events
   */
  async verifyIntegrity(params?: {
    startDate?: string;
    endDate?: string;
    eventIds?: string[];
  }): Promise<{
    verified: boolean;
    totalChecked: number;
    validCount: number;
    invalidCount: number;
    invalidEvents: string[];
    constitutionalHash: string;
  }> {
    const response = await this.client.post<{
      verified: boolean;
      totalChecked: number;
      validCount: number;
      invalidCount: number;
      invalidEvents: string[];
      constitutionalHash: string;
    }>(`${this.basePath}/verify`, {
      ...params,
      constitutionalHash: CONSTITUTIONAL_HASH,
    });

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to verify audit integrity');
    }

    return response.data;
  }

  // ===========================================================================
  // Helpers
  // ===========================================================================

  private validateEvent(data: unknown): AuditEvent {
    const result = AuditEventSchema.safeParse(data);
    if (!result.success) {
      throw new ValidationError('Invalid audit event data', {
        validation: result.error.errors.map((e) => e.message),
      });
    }
    return result.data;
  }
}
