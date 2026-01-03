/**
 * ACGS-2 Enterprise TypeScript SDK
 * Constitutional Hash: cdd01ef066bc6cf2
 */

import { EventEmitter } from 'eventemitter3';
import { z } from 'zod';
import { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { createHttpClient } from './http';
import { TenantContext } from './tenant';
import { AuthManager } from '../auth/auth-manager';
import { PolicyService } from '../services/policy-service';
import { AuditService } from '../services/audit-service';
import { AgentService } from '../services/agent-service';
import { TenantService } from '../services/tenant-service';

// Configuration schemas
export const SDKConfigSchema = z.object({
  baseURL: z.string().url(),
  tenantId: z.string().min(1),
  constitutionalHash: z.literal('cdd01ef066bc6cf2'),
  timeout: z.number().min(1000).max(30000).default(10000),
  retryAttempts: z.number().min(0).max(5).default(3),
  retryDelay: z.number().min(100).max(5000).default(1000),
  enableMetrics: z.boolean().default(true),
  enableTracing: z.boolean().default(true),
  environment: z.enum(['development', 'staging', 'production']).default('production'),
});

export type SDKConfig = z.infer<typeof SDKConfigSchema>;

export const TenantConfigSchema = z.object({
  tenantId: z.string().min(1),
  tenantTier: z.enum(['free', 'professional', 'enterprise', 'sovereign']),
  resourceQuota: z.object({
    users: z.number().min(1),
    policies: z.number().min(1),
    agents: z.number().min(1),
    apiCalls: z.number().min(1),
    storage: z.number().min(1),
  }),
  complianceFrameworks: z.array(z.string()).default([]),
  dataResidency: z.string().optional(),
  features: z.array(z.string()).default([]),
});

export type TenantConfig = z.infer<typeof TenantConfigSchema>;

// SDK Events
export interface SDKEvents {
  ready: () => void;
  error: (error: Error) => void;
  tenantSwitched: (tenantId: string) => void;
  authenticated: (userId: string) => void;
  deauthenticated: () => void;
  rateLimited: (retryAfter: number) => void;
  quotaExceeded: (resource: string, limit: number) => void;
}

/**
 * ACGS-2 Enterprise SDK Client
 * Multi-tenant AI Governance Platform SDK with constitutional compliance
 */
export class ACGS2Client extends EventEmitter<SDKEvents> {
  private readonly config: SDKConfig;
  private readonly httpClient: AxiosInstance;
  private currentTenant: TenantContext;
  private isReady = false;

  // Core services
  public readonly auth: AuthManager;
  public readonly policies: PolicyService;
  public readonly audit: AuditService;
  public readonly agents: AgentService;
  public readonly tenants: TenantService;

  constructor(config: SDKConfig) {
    super();

    // Validate configuration
    this.config = SDKConfigSchema.parse(config);

    // Initialize HTTP client
    this.httpClient = createHttpClient(this.config, this.handleRequestError.bind(this));

    // Initialize tenant context
    this.currentTenant = new TenantContext({
      tenantId: this.config.tenantId,
      constitutionalHash: this.config.constitutionalHash,
      environment: this.config.environment,
    });

    // Initialize services
    this.auth = new AuthManager(this.httpClient, this.currentTenant);
    this.policies = new PolicyService(this.httpClient, this.currentTenant);
    this.audit = new AuditService(this.httpClient, this.currentTenant);
    this.agents = new AgentService(this.httpClient, this.currentTenant);
    this.tenants = new TenantService(this.httpClient, this.currentTenant);

    // Set up event forwarding
    this.setupEventForwarding();
  }

  /**
   * Initialize the SDK and establish connections
   */
  async initialize(): Promise<void> {
    try {
      // Validate tenant access
      await this.tenants.validateTenantAccess(this.config.tenantId);

      // Initialize services
      await Promise.all([
        this.auth.initialize(),
        this.policies.initialize(),
        this.audit.initialize(),
        this.agents.initialize(),
      ]);

      this.isReady = true;
      this.emit('ready');

    } catch (error) {
      this.emit('error', error as Error);
      throw error;
    }
  }

  /**
   * Switch to a different tenant context
   */
  async switchTenant(tenantId: string): Promise<void> {
    if (!this.isReady) {
      throw new Error('SDK not initialized. Call initialize() first.');
    }

    try {
      // Validate new tenant access
      await this.tenants.validateTenantAccess(tenantId);

      // Update tenant context
      this.currentTenant = new TenantContext({
        tenantId,
        constitutionalHash: this.config.constitutionalHash,
        environment: this.config.environment,
      });

      // Re-initialize services with new tenant
      await Promise.all([
        this.auth.switchTenant(this.currentTenant),
        this.policies.switchTenant(this.currentTenant),
        this.audit.switchTenant(this.currentTenant),
        this.agents.switchTenant(this.currentTenant),
      ]);

      this.emit('tenantSwitched', tenantId);

    } catch (error) {
      this.emit('error', error as Error);
      throw error;
    }
  }

  /**
   * Get current tenant information
   */
  getCurrentTenant(): TenantContext {
    return this.currentTenant;
  }

  /**
   * Check if SDK is ready for use
   */
  isInitialized(): boolean {
    return this.isReady;
  }

  /**
   * Get SDK configuration (without sensitive data)
   */
  getConfig(): Omit<SDKConfig, 'timeout' | 'retryAttempts' | 'retryDelay'> {
    return {
      baseURL: this.config.baseURL,
      tenantId: this.config.tenantId,
      constitutionalHash: this.config.constitutionalHash,
      enableMetrics: this.config.enableMetrics,
      enableTracing: this.config.enableTracing,
      environment: this.config.environment,
    };
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<{
    status: 'healthy' | 'degraded' | 'unhealthy';
    services: Record<string, boolean>;
    timestamp: Date;
  }> {
    const services = {
      auth: await this.auth.healthCheck(),
      policies: await this.policies.healthCheck(),
      audit: await this.audit.healthCheck(),
      agents: await this.agents.healthCheck(),
    };

    const healthyCount = Object.values(services).filter(Boolean).length;
    const totalCount = Object.keys(services).length;

    let status: 'healthy' | 'degraded' | 'unhealthy';
    if (healthyCount === totalCount) {
      status = 'healthy';
    } else if (healthyCount >= totalCount / 2) {
      status = 'degraded';
    } else {
      status = 'unhealthy';
    }

    return {
      status,
      services,
      timestamp: new Date(),
    };
  }

  /**
   * Get metrics (if enabled)
   */
  getMetrics(): Record<string, any> {
    if (!this.config.enableMetrics) {
      return {};
    }

    return {
      tenantId: this.currentTenant.tenantId,
      environment: this.config.environment,
      services: {
        auth: this.auth.getMetrics(),
        policies: this.policies.getMetrics(),
        audit: this.audit.getMetrics(),
        agents: this.agents.getMetrics(),
      },
      timestamp: new Date().toISOString(),
    };
  }

  /**
   * Clean up resources
   */
  async dispose(): Promise<void> {
    this.isReady = false;

    await Promise.all([
      this.auth.dispose(),
      this.policies.dispose(),
      this.audit.dispose(),
      this.agents.dispose(),
    ]);

    this.removeAllListeners();
  }

  /**
   * Handle HTTP request errors
   */
  private handleRequestError(error: any): void {
    if (error.response?.status === 429) {
      const retryAfter = error.response.headers['retry-after'] || 60;
      this.emit('rateLimited', parseInt(retryAfter));
    } else if (error.response?.status === 403 && error.response.data?.code === 'QUOTA_EXCEEDED') {
      const resource = error.response.data?.resource || 'unknown';
      const limit = error.response.data?.limit || 0;
      this.emit('quotaExceeded', resource, limit);
    }

    this.emit('error', error);
  }

  /**
   * Set up event forwarding from services
   */
  private setupEventForwarding(): void {
    // Forward auth events
    this.auth.on('authenticated', (userId) => this.emit('authenticated', userId));
    this.auth.on('deauthenticated', () => this.emit('deauthenticated'));

    // Forward service errors
    [this.auth, this.policies, this.audit, this.agents].forEach(service => {
      service.on('error', (error) => this.emit('error', error));
    });
  }
}

/**
 * Create ACGS-2 SDK instance
 */
export function createACGS2Client(config: SDKConfig): ACGS2Client {
  return new ACGS2Client(config);
}

/**
 * Default SDK configuration factory
 */
export function createDefaultConfig(baseURL: string, tenantId: string): SDKConfig {
  return {
    baseURL,
    tenantId,
    constitutionalHash: 'cdd01ef066bc6cf2',
    timeout: 10000,
    retryAttempts: 3,
    retryDelay: 1000,
    enableMetrics: true,
    enableTracing: true,
    environment: 'production',
  };
}
