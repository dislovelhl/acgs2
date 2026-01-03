/**
 * ACGS-2 TypeScript SDK
 * AI Constitutional Governance System
 *
 * Constitutional Hash: cdd01ef066bc6cf2
 *
 * @packageDocumentation
 */

// =============================================================================
// Core Exports
// =============================================================================

export { ACGS2Client, createClient, type ClientConfig } from './client';

// =============================================================================
// Service Exports
// =============================================================================

export {
  PolicyService,
  AgentService,
  ComplianceService,
  AuditService,
  GovernanceService,
  HITLApprovalsService,
  MLGovernanceService,
  type AgentInfo,
  type AgentRegistration,
  type ComplianceReport,
  type ComplianceRule,
  type ComplianceViolation,
  type CreateAuditEventRequest,
  type AuditTrail,
  type AuditExport,
  type AuditStatistics,
  type GovernancePolicy,
  type GovernanceRule,
  type EscalationPath,
  type GovernanceMetrics,
} from './services';

// =============================================================================
// Type Exports
// =============================================================================

export {
  // Constants
  CONSTITUTIONAL_HASH,

  // Enums
  MessageType,
  Priority,
  PolicyStatus,
  ApprovalStatus,
  ComplianceStatus,
  EventSeverity,
  EventCategory,
  ModelTrainingStatus,
  DriftDirection,
  ABNTestStatus,

  // Zod Schemas
  ConstitutionalHashSchema,
  AgentMessageSchema,
  PolicySchema,
  ComplianceResultSchema,
  ApprovalRequestSchema,
  AuditEventSchema,
  GovernanceDecisionSchema,
  MLModelSchema,
  ModelPredictionSchema,
  DriftDetectionSchema,
  ABNTestSchema,
  FeedbackSubmissionSchema,

  // Inferred Types
  type AgentMessage,
  type Policy,
  type ComplianceResult,
  type ApprovalRequest,
  type AuditEvent,
  type GovernanceDecision,
  type MLModel,
  type ModelPrediction,
  type DriftDetection,
  type ABNTest,
  type FeedbackSubmission,

  // API Types
  type PaginationParams,
  type PaginatedResponse,
  type ApiError,
  type ApiResponse,

  // Configuration Types
  type ACGS2Config,
  type AuthConfig,

  // Event Types
  type ACGS2Event,
  type EventHandler,

  // Service Request Types
  type CreatePolicyRequest,
  type UpdatePolicyRequest,
  type SendMessageRequest,
  type CreateApprovalRequest,
  type SubmitApprovalDecision,
  type ValidateComplianceRequest,
  type QueryAuditEventsRequest,
  type CreateMLModelRequest,
  type UpdateMLModelRequest,
  type MakePredictionRequest,
  type SubmitFeedbackRequest,
  type CreateABNTestRequest,
} from './types';

// =============================================================================
// Utility Exports
// =============================================================================

export {
  // Constitutional Validation
  validateConstitutionalHash,
  assertConstitutionalHash,

  // Errors
  ACGS2Error,
  ConstitutionalHashMismatchError,
  AuthenticationError,
  AuthorizationError,
  ValidationError,
  NetworkError,
  RateLimitError,
  TimeoutError,

  // UUID Generation
  generateUUID,

  // Date/Time Utilities
  nowISO,
  parseISO,
  isExpired,

  // Retry Logic
  withRetry,
  sleep,
  type RetryOptions,

  // Object Utilities
  deepClone,
  deepMerge,
  omit,
  pick,

  // URL Utilities
  joinUrl,
  buildQueryString,

  // Hashing
  simpleHash,
  createDeterministicId,

  // Type Guards
  isObject,
  isNonEmptyString,
  isUUID,

  // Logging
  createLogger,
  silentLogger,
  type Logger,
  type LogLevel,
} from './utils';

// =============================================================================
// ACGS2 SDK Factory
// =============================================================================

import { ACGS2Client, ClientConfig } from './client';
import { PolicyService } from './services/policy';
import { AgentService } from './services/agent';
import { ComplianceService } from './services/compliance';
import { AuditService } from './services/audit';
import { GovernanceService } from './services/governance';
import { HITLApprovalsService } from './services/hitl-approvals';
import { MLGovernanceService } from './services/ml-governance';
import { CONSTITUTIONAL_HASH } from './types';
import { createLogger, silentLogger } from './utils';

/**
 * ACGS-2 SDK instance with all services pre-configured
 */
export interface ACGS2SDK {
  /** HTTP client for direct API calls */
  client: ACGS2Client;

  /** Policy management service */
  policies: PolicyService;

  /** Agent management and messaging service */
  agents: AgentService;

  /** Compliance validation service */
  compliance: ComplianceService;

  /** Audit logging and querying service */
  audit: AuditService;

  /** Governance and approval service */
  governance: GovernanceService;

  /** Human-in-the-Loop approval workflows service */
  hitlApprovals: HITLApprovalsService;

  /** ML governance and adaptive learning service */
  mlGovernance: MLGovernanceService;

  /** Constitutional hash for this SDK instance */
  constitutionalHash: string;

  /** Performs a health check on the API */
  healthCheck(): Promise<{ healthy: boolean; latencyMs: number }>;
}

/**
 * Creates a fully configured ACGS-2 SDK instance
 *
 * @example
 * ```typescript
 * import { createACGS2SDK } from '@acgs/sdk';
 *
 * const sdk = createACGS2SDK({
 *   baseUrl: 'https://api.acgs.io',
 *   apiKey: 'your-api-key',
 *   tenantId: 'your-tenant-id',
 * });
 *
 * // Use services
 * const policies = await sdk.policies.list();
 * const compliance = await sdk.compliance.validate({
 *   policyId: 'policy-id',
 *   context: { action: 'deploy', risk: 'low' }
 * });
 * ```
 */
export function createACGS2SDK(config: ClientConfig): ACGS2SDK {
  const logger = config.logger ?? (process.env['NODE_ENV'] === 'development' ? createLogger() : silentLogger);
  const client = new ACGS2Client({ ...config, logger });

  return {
    client,
    policies: new PolicyService(client),
    agents: new AgentService(client, { logger }),
    compliance: new ComplianceService(client),
    audit: new AuditService(client),
    governance: new GovernanceService(client),
    hitlApprovals: new HITLApprovalsService(client),
    mlGovernance: new MLGovernanceService(client),
    constitutionalHash: CONSTITUTIONAL_HASH,
    healthCheck: () => client.healthCheck(),
  };
}

// Default export
export default createACGS2SDK;
