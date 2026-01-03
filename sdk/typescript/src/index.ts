import { getLogger } from '../../../../../sdk/typescript/src/utils/logger';
const logger = getLogger('index');


/**
 * ACGS-2 Enterprise TypeScript SDK
 * Constitutional AI Governance Platform
 *
 * Constitutional Hash: cdd01ef066bc6cf2
 *
 * @packageDocumentation
 */

// Core exports
export {
  ACGS2Client,
  createACGS2Client,
  createDefaultConfig,
  SDKConfig,
  TenantConfig,
  SDKEvents,
} from './core/client';

export {
  TenantContext,
  createTenantContext,
  createDefaultTenantContext,
  TenantContextData,
  TenantContextEvents,
} from './core/tenant';

export {
  EnterpriseHttpClient,
  createHttpClient,
  HttpClientConfig,
  RequestMetrics,
  TracingHeaders,
  RequestInterceptor,
  ResponseInterceptor,
  ErrorInterceptor,
} from './core/http';

// Auth exports
export {
  AuthManager,
  AuthEvents,
  LoginRequest,
  LoginResponse,
  TokenRefreshRequest,
  TokenRefreshResponse,
  UserInfo,
  AuthState,
} from './auth/auth-manager';

export {
  JWTManager,
  JWTOptions,
  TokenPayload,
  TokenVerificationResult,
} from './auth/jwt-manager';

export {
  OktaAuthProvider,
  OktaConfig,
  OktaAuthState,
} from './auth/providers/okta-provider';

export {
  AzureADAuthProvider,
  AzureADConfig,
  AzureADAuthState,
} from './auth/providers/azure-ad-provider';

// Service exports
export {
  PolicyService,
  PolicyEvents,
  Policy,
  PolicyRule,
  PolicyValidationResult,
  CreatePolicyRequest,
  UpdatePolicyRequest,
  PolicyQuery,
} from './services/policy-service';

export {
  AuditService,
  AuditEvents,
  AuditEvent,
  AuditQuery,
  AuditSummary,
  ComplianceReport,
} from './services/audit-service';

export {
  AgentService,
  AgentEvents,
  Agent,
  AgentStatus,
  AgentCapabilities,
  AgentHeartbeat,
  RegisterAgentRequest,
  UpdateAgentRequest,
  AgentQuery,
} from './services/agent-service';

export {
  TenantService,
  TenantEvents,
  Tenant,
  TenantStatus,
  TenantTier,
  TenantResourceQuota,
  CreateTenantRequest,
  UpdateTenantRequest,
  TenantQuery,
} from './services/tenant-service';

// Model exports
export * from './models/common';
export * from './models/errors';
export * from './models/responses';

// Utility exports
export * from './utils/validation';
export * from './utils/retry';
export * from './utils/rate-limiting';
export * from './utils/circuit-breaker';

// Middleware exports
export * from './middleware/auth-middleware';
export * from './middleware/tenant-middleware';
export * from './middleware/rate-limit-middleware';
export * from './middleware/compliance-middleware';

// Types
export type {
  AxiosInstance,
  AxiosRequestConfig,
  AxiosResponse,
} from 'axios';

// Version info
export const VERSION = '3.0.0';
export const CONSTITUTIONAL_HASH = 'cdd01ef066bc6cf2';

/**
 * Quick start example:
 *
 * ```typescript
 * import { createACGS2Client, createDefaultConfig } from '@acgs2/sdk';
 *
 * // Create client configuration
 * const config = createDefaultConfig('https://api.acgs2.com', 'my-tenant-id');
 *
 * // Create and initialize client
 * const client = createACGS2Client(config);
 * await client.initialize();
 *
 * // Use services
 * const policies = await client.policies.list();
 * const agents = await client.agents.list();
 *
 * // Clean up when done
 * await client.dispose();
 * ```
 *
 * Advanced usage with custom configuration:
 *
 * ```typescript
 * import { ACGS2Client } from '@acgs2/sdk';
 *
 * const client = new ACGS2Client({
 *   baseURL: 'https://api.acgs2.com',
 *   tenantId: 'my-tenant-id',
 *   constitutionalHash: 'cdd01ef066bc6cf2',
 *   timeout: 15000,
 *   retryAttempts: 5,
 *   enableMetrics: true,
 *   enableTracing: true,
 *   logger.info('ACGS-2 SDK ready!';
 * });
 *
 * client.on('ready', () => {
 *   console.log('ACGS-2 SDK ready!');
 * });
 *
 * client.on('error', (error) => {
 *   console.error('SDK error:', error);
 * });
 *
 * await client.initialize();
 * ```
 */
