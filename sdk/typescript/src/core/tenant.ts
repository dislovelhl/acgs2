/**
 * ACGS-2 Tenant Context Management
 * Constitutional Hash: cdd01ef066bc6cf2
 */

import { z } from 'zod';
import { EventEmitter } from 'eventemitter3';

// Tenant context schema
export const TenantContextSchema = z.object({
  tenantId: z.string().min(1),
  constitutionalHash: z.literal('cdd01ef066bc6cf2'),
  environment: z.enum(['development', 'staging', 'production']),
  userId: z.string().optional(),
  sessionId: z.string().optional(),
  permissions: z.array(z.string()).default([]),
  quota: z.object({
    users: z.number().min(0),
    policies: z.number().min(0),
    agents: z.number().min(0),
    apiCalls: z.number().min(0),
    storage: z.number().min(0),
  }).optional(),
  features: z.array(z.string()).default([]),
  complianceFrameworks: z.array(z.string()).default([]),
  dataResidency: z.string().optional(),
  createdAt: z.date().optional(),
  updatedAt: z.date().optional(),
});

export type TenantContextData = z.infer<typeof TenantContextSchema>;

// Tenant context events
export interface TenantContextEvents {
  updated: (context: TenantContext) => void;
  permissionChanged: (permissions: string[]) => void;
  quotaUpdated: (quota: TenantContextData['quota']) => void;
}

/**
 * Tenant Context Manager
 * Handles multi-tenant isolation and context management
 */
export class TenantContext extends EventEmitter<TenantContextEvents> {
  private data: TenantContextData;
  private readonly contextId: string;

  constructor(initialData: Omit<TenantContextData, 'createdAt' | 'updatedAt'>) {
    super();

    this.contextId = this.generateContextId();
    this.data = {
      ...initialData,
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    // Validate data
    this.validate();
  }

  /**
   * Get tenant ID
   */
  get tenantId(): string {
    return this.data.tenantId;
  }

  /**
   * Get constitutional hash
   */
  get constitutionalHash(): string {
    return this.data.constitutionalHash;
  }

  /**
   * Get environment
   */
  get environment(): TenantContextData['environment'] {
    return this.data.environment;
  }

  /**
   * Get current user ID
   */
  get userId(): string | undefined {
    return this.data.userId;
  }

  /**
   * Set current user ID
   */
  setUserId(userId: string | undefined): void {
    const oldUserId = this.data.userId;
    this.data.userId = userId;
    this.data.updatedAt = new Date();

    if (oldUserId !== userId) {
      this.emit('updated', this);
    }
  }

  /**
   * Get session ID
   */
  get sessionId(): string | undefined {
    return this.data.sessionId;
  }

  /**
   * Set session ID
   */
  setSessionId(sessionId: string | undefined): void {
    this.data.sessionId = sessionId;
    this.data.updatedAt = new Date();
    this.emit('updated', this);
  }

  /**
   * Get permissions
   */
  get permissions(): string[] {
    return [...this.data.permissions];
  }

  /**
   * Set permissions
   */
  setPermissions(permissions: string[]): void {
    const oldPermissions = [...this.data.permissions];
    this.data.permissions = [...permissions];
    this.data.updatedAt = new Date();

    if (JSON.stringify(oldPermissions.sort()) !== JSON.stringify(permissions.sort())) {
      this.emit('permissionChanged', permissions);
      this.emit('updated', this);
    }
  }

  /**
   * Check if user has permission
   */
  hasPermission(permission: string): boolean {
    return this.data.permissions.includes(permission);
  }

  /**
   * Check if user has any of the permissions
   */
  hasAnyPermission(permissions: string[]): boolean {
    return permissions.some(permission => this.hasPermission(permission));
  }

  /**
   * Check if user has all permissions
   */
  hasAllPermissions(permissions: string[]): boolean {
    return permissions.every(permission => this.hasPermission(permission));
  }

  /**
   * Get quota information
   */
  get quota(): TenantContextData['quota'] {
    return this.data.quota ? { ...this.data.quota } : undefined;
  }

  /**
   * Set quota information
   */
  setQuota(quota: TenantContextData['quota']): void {
    const oldQuota = this.data.quota;
    this.data.quota = quota ? { ...quota } : undefined;
    this.data.updatedAt = new Date();

    if (JSON.stringify(oldQuota) !== JSON.stringify(quota)) {
      this.emit('quotaUpdated', quota);
      this.emit('updated', this);
    }
  }

  /**
   * Check if quota allows operation
   */
  checkQuota(resource: keyof NonNullable<TenantContextData['quota']>, amount: number = 1): boolean {
    if (!this.data.quota) return true;
    const current = this.data.quota[resource] || 0;
    return current >= amount;
  }

  /**
   * Get features
   */
  get features(): string[] {
    return [...this.data.features];
  }

  /**
   * Set features
   */
  setFeatures(features: string[]): void {
    this.data.features = [...features];
    this.data.updatedAt = new Date();
    this.emit('updated', this);
  }

  /**
   * Check if tenant has feature
   */
  hasFeature(feature: string): boolean {
    return this.data.features.includes(feature);
  }

  /**
   * Get compliance frameworks
   */
  get complianceFrameworks(): string[] {
    return [...this.data.complianceFrameworks];
  }

  /**
   * Set compliance frameworks
   */
  setComplianceFrameworks(frameworks: string[]): void {
    this.data.complianceFrameworks = [...frameworks];
    this.data.updatedAt = new Date();
    this.emit('updated', this);
  }

  /**
   * Get data residency region
   */
  get dataResidency(): string | undefined {
    return this.data.dataResidency;
  }

  /**
   * Set data residency region
   */
  setDataResidency(residency: string | undefined): void {
    this.data.dataResidency = residency;
    this.data.updatedAt = new Date();
    this.emit('updated', this);
  }

  /**
   * Get context creation timestamp
   */
  get createdAt(): Date | undefined {
    return this.data.createdAt;
  }

  /**
   * Get context last update timestamp
   */
  get updatedAt(): Date | undefined {
    return this.data.updatedAt;
  }

  /**
   * Get context ID (unique identifier for this context instance)
   */
  getContextId(): string {
    return this.contextId;
  }

  /**
   * Export context data for serialization
   */
  toJSON(): TenantContextData {
    return {
      ...this.data,
      permissions: [...this.data.permissions],
      features: [...this.data.features],
      complianceFrameworks: [...this.data.complianceFrameworks],
    };
  }

  /**
   * Create context from serialized data
   */
  static fromJSON(data: TenantContextData): TenantContext {
    const context = new TenantContext(data);
    if (data.createdAt) {
      context.data.createdAt = new Date(data.createdAt);
    }
    if (data.updatedAt) {
      context.data.updatedAt = new Date(data.updatedAt);
    }
    return context;
  }

  /**
   * Clone context
   */
  clone(): TenantContext {
    return TenantContext.fromJSON(this.toJSON());
  }

  /**
   * Validate context data
   */
  private validate(): void {
    try {
      TenantContextSchema.parse(this.data);
    } catch (error) {
      throw new Error(`Invalid tenant context: ${error}`);
    }
  }

  /**
   * Generate unique context ID
   */
  private generateContextId(): string {
    return `ctx_${this.data.tenantId}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Get headers for API requests
   */
  getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'X-Tenant-ID': this.tenantId,
      'X-Constitutional-Hash': this.constitutionalHash,
      'X-Environment': this.environment,
      'X-Context-ID': this.contextId,
    };

    if (this.userId) {
      headers['X-User-ID'] = this.userId;
    }

    if (this.sessionId) {
      headers['X-Session-ID'] = this.sessionId;
    }

    return headers;
  }

  /**
   * Get metadata for logging and monitoring
   */
  getMetadata(): Record<string, any> {
    return {
      tenantId: this.tenantId,
      constitutionalHash: this.constitutionalHash,
      environment: this.environment,
      contextId: this.contextId,
      userId: this.userId,
      sessionId: this.sessionId,
      permissions: this.permissions,
      features: this.features,
      complianceFrameworks: this.complianceFrameworks,
      dataResidency: this.dataResidency,
      createdAt: this.createdAt?.toISOString(),
      updatedAt: this.updatedAt?.toISOString(),
    };
  }
}

/**
 * Create tenant context
 */
export function createTenantContext(data: Omit<TenantContextData, 'createdAt' | 'updatedAt'>): TenantContext {
  return new TenantContext(data);
}

/**
 * Default tenant context factory
 */
export function createDefaultTenantContext(tenantId: string, environment: TenantContextData['environment'] = 'production'): TenantContext {
  return new TenantContext({
    tenantId,
    constitutionalHash: 'cdd01ef066bc6cf2',
    environment,
    permissions: [],
    features: [],
    complianceFrameworks: [],
  });
}
