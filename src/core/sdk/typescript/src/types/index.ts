/**
 * ACGS-2 TypeScript SDK Types
 * Constitutional Hash: cdd01ef066bc6cf2
 */

import { z } from 'zod';

// =============================================================================
// Constitutional Constants
// =============================================================================

export const CONSTITUTIONAL_HASH = 'cdd01ef066bc6cf2';

// =============================================================================
// Enums
// =============================================================================

export enum MessageType {
  COMMAND = 'command',
  QUERY = 'query',
  EVENT = 'event',
  RESPONSE = 'response',
  ERROR = 'error',
}

export enum Priority {
  CRITICAL = 'critical',
  HIGH = 'high',
  NORMAL = 'normal',
  LOW = 'low',
}

export enum PolicyStatus {
  DRAFT = 'draft',
  PENDING_REVIEW = 'pending_review',
  APPROVED = 'approved',
  ACTIVE = 'active',
  DEPRECATED = 'deprecated',
  ARCHIVED = 'archived',
}

export enum ApprovalStatus {
  PENDING = 'pending',
  APPROVED = 'approved',
  REJECTED = 'rejected',
  ESCALATED = 'escalated',
  EXPIRED = 'expired',
}

export enum ComplianceStatus {
  COMPLIANT = 'compliant',
  NON_COMPLIANT = 'non_compliant',
  PENDING_REVIEW = 'pending_review',
  UNKNOWN = 'unknown',
}

export enum EventSeverity {
  DEBUG = 'debug',
  INFO = 'info',
  WARNING = 'warning',
  ERROR = 'error',
  CRITICAL = 'critical',
}

export enum EventCategory {
  GOVERNANCE = 'governance',
  POLICY = 'policy',
  AGENT = 'agent',
  AUTHENTICATION = 'authentication',
  AUTHORIZATION = 'authorization',
  AUDIT = 'audit',
  SYSTEM = 'system',
  ML_MODEL = 'ml_model',
  PREDICTION = 'prediction',
}

export enum ModelTrainingStatus {
  TRAINING = 'training',
  COMPLETED = 'completed',
  FAILED = 'failed',
  STOPPED = 'stopped',
}

export enum DriftDirection {
  NONE = 'none',
  INCREASE = 'increase',
  DECREASE = 'decrease',
}

export enum ABNTestStatus {
  ACTIVE = 'active',
  COMPLETED = 'completed',
  PAUSED = 'paused',
  CANCELLED = 'cancelled',
}

// =============================================================================
// Zod Schemas
// =============================================================================

export const ConstitutionalHashSchema = z.literal(CONSTITUTIONAL_HASH);

export const AgentMessageSchema = z.object({
  id: z.string().uuid(),
  type: z.nativeEnum(MessageType),
  priority: z.nativeEnum(Priority),
  sourceAgentId: z.string(),
  targetAgentId: z.string().optional(),
  payload: z.record(z.unknown()),
  timestamp: z.string().datetime(),
  correlationId: z.string().uuid().optional(),
  constitutionalHash: ConstitutionalHashSchema,
  metadata: z.record(z.string()).optional(),
});

export const PolicySchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1).max(255),
  version: z.string(),
  description: z.string().optional(),
  status: z.nativeEnum(PolicyStatus),
  rules: z.array(z.record(z.unknown())),
  constitutionalHash: ConstitutionalHashSchema,
  tenantId: z.string().optional(),
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
  createdBy: z.string(),
  tags: z.array(z.string()).optional(),
  complianceTags: z.array(z.string()).optional(),
});

export const ComplianceResultSchema = z.object({
  policyId: z.string().uuid(),
  status: z.nativeEnum(ComplianceStatus),
  score: z.number().min(0).max(100),
  violations: z.array(z.object({
    ruleId: z.string(),
    message: z.string(),
    severity: z.nativeEnum(EventSeverity),
  })),
  timestamp: z.string().datetime(),
  constitutionalHash: ConstitutionalHashSchema,
});

export const ApprovalRequestSchema = z.object({
  id: z.string().uuid(),
  requestType: z.string(),
  requesterId: z.string(),
  status: z.nativeEnum(ApprovalStatus),
  riskScore: z.number().min(0).max(100),
  requiredApprovers: z.number().min(1),
  currentApprovals: z.number(),
  decisions: z.array(z.object({
    approverId: z.string(),
    decision: z.nativeEnum(ApprovalStatus),
    reasoning: z.string().optional(),
    timestamp: z.string().datetime(),
  })),
  payload: z.record(z.unknown()),
  createdAt: z.string().datetime(),
  expiresAt: z.string().datetime().optional(),
  constitutionalHash: ConstitutionalHashSchema,
});

export const AuditEventSchema = z.object({
  id: z.string().uuid(),
  category: z.nativeEnum(EventCategory),
  severity: z.nativeEnum(EventSeverity),
  action: z.string(),
  actor: z.string(),
  resource: z.string(),
  resourceId: z.string().optional(),
  outcome: z.enum(['success', 'failure', 'partial']),
  details: z.record(z.unknown()).optional(),
  timestamp: z.string().datetime(),
  constitutionalHash: ConstitutionalHashSchema,
  tenantId: z.string().optional(),
  correlationId: z.string().uuid().optional(),
});

export const GovernanceDecisionSchema = z.object({
  id: z.string().uuid(),
  requestId: z.string().uuid(),
  decision: z.enum(['approve', 'deny', 'escalate']),
  reasoning: z.string(),
  policyViolations: z.array(z.string()),
  riskScore: z.number().min(0).max(100),
  reviewerIds: z.array(z.string()),
  timestamp: z.string().datetime(),
  constitutionalHash: ConstitutionalHashSchema,
  blockchainAnchor: z.string().optional(),
});

// =============================================================================
// Inferred Types
// =============================================================================

export type AgentMessage = z.infer<typeof AgentMessageSchema>;
export type Policy = z.infer<typeof PolicySchema>;
export type ComplianceResult = z.infer<typeof ComplianceResultSchema>;
export type ApprovalRequest = z.infer<typeof ApprovalRequestSchema>;
export type AuditEvent = z.infer<typeof AuditEventSchema>;
export type GovernanceDecision = z.infer<typeof GovernanceDecisionSchema>;

// =============================================================================
// API Types
// =============================================================================

export interface PaginationParams {
  page?: number;
  pageSize?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  constitutionalHash: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: ApiError;
  constitutionalHash: string;
  requestId: string;
  timestamp: string;
}

// =============================================================================
// Configuration Types
// =============================================================================

export interface ACGS2Config {
  baseUrl: string;
  apiKey?: string;
  accessToken?: string;
  tenantId?: string;
  timeout?: number;
  retryAttempts?: number;
  retryDelay?: number;
  validateConstitutionalHash?: boolean;
  onError?: (error: ApiError) => void;
  onConstitutionalViolation?: (expected: string, received: string) => void;
}

export interface AuthConfig {
  type: 'api_key' | 'bearer' | 'oauth2';
  apiKey?: string;
  accessToken?: string;
  refreshToken?: string;
  tokenEndpoint?: string;
  clientId?: string;
  clientSecret?: string;
  scope?: string[];
}

// =============================================================================
// Event Types
// =============================================================================

export interface ACGS2Event<T = unknown> {
  type: string;
  payload: T;
  timestamp: string;
  constitutionalHash: string;
}

export type EventHandler<T = unknown> = (event: ACGS2Event<T>) => void | Promise<void>;

// =============================================================================
// Service Types
// =============================================================================

export interface CreatePolicyRequest {
  name: string;
  description?: string;
  rules: Record<string, unknown>[];
  tags?: string[];
  complianceTags?: string[];
}

export interface UpdatePolicyRequest {
  name?: string;
  description?: string;
  rules?: Record<string, unknown>[];
  status?: PolicyStatus;
  tags?: string[];
  complianceTags?: string[];
}

export interface SendMessageRequest {
  type: MessageType;
  priority?: Priority;
  targetAgentId?: string;
  payload: Record<string, unknown>;
  correlationId?: string;
  metadata?: Record<string, string>;
}

export interface CreateApprovalRequest {
  requestType: string;
  payload: Record<string, unknown>;
  riskScore?: number;
  requiredApprovers?: number;
}

export interface SubmitApprovalDecision {
  decision: 'approve' | 'reject';
  reasoning: string;
}

export interface ValidateComplianceRequest {
  policyId: string;
  context: Record<string, unknown>;
}

export interface QueryAuditEventsRequest extends PaginationParams {
  category?: EventCategory;
  severity?: EventSeverity;
  actor?: string;
  resource?: string;
  startTime?: string;
  endTime?: string;
}

// =============================================================================
// ML Governance Types
// =============================================================================

export const MLModelSchema = z.object({
  id: z.string(),
  name: z.string(),
  version: z.string(),
  description: z.string().optional(),
  modelType: z.string(),
  framework: z.string(),
  accuracyScore: z.number().optional(),
  trainingStatus: z.nativeEnum(ModelTrainingStatus),
  lastTrainedAt: z.string().optional(),
  createdAt: z.string(),
  updatedAt: z.string(),
  constitutionalHash: ConstitutionalHashSchema,
});

export const ModelPredictionSchema = z.object({
  id: z.string(),
  modelId: z.string(),
  modelVersion: z.string(),
  inputFeatures: z.record(z.unknown()),
  prediction: z.unknown(),
  confidenceScore: z.number().optional(),
  predictionMetadata: z.record(z.unknown()).optional(),
  timestamp: z.string(),
  constitutionalHash: ConstitutionalHashSchema,
});

export const DriftDetectionSchema = z.object({
  modelId: z.string(),
  driftScore: z.number(),
  driftDirection: z.nativeEnum(DriftDirection),
  baselineAccuracy: z.number(),
  currentAccuracy: z.number(),
  featuresAffected: z.array(z.string()),
  detectedAt: z.string(),
  recommendations: z.array(z.string()),
  constitutionalHash: ConstitutionalHashSchema,
});

export const ABNTestSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string().optional(),
  modelAId: z.string(),
  modelBId: z.string(),
  status: z.nativeEnum(ABNTestStatus),
  testDurationDays: z.number(),
  trafficSplitPercentage: z.number(),
  successMetric: z.string(),
  createdAt: z.string(),
  completedAt: z.string().optional(),
  constitutionalHash: ConstitutionalHashSchema,
});

export const FeedbackSubmissionSchema = z.object({
  id: z.string(),
  predictionId: z.string().optional(),
  modelId: z.string(),
  feedbackType: z.string(),
  feedbackValue: z.unknown(),
  userId: z.string().optional(),
  context: z.record(z.unknown()).optional(),
  submittedAt: z.string(),
  constitutionalHash: ConstitutionalHashSchema,
});

// Type exports
export type MLModel = z.infer<typeof MLModelSchema>;
export type ModelPrediction = z.infer<typeof ModelPredictionSchema>;
export type DriftDetection = z.infer<typeof DriftDetectionSchema>;
export type ABNTest = z.infer<typeof ABNTestSchema>;
export type FeedbackSubmission = z.infer<typeof FeedbackSubmissionSchema>;

// Request interfaces for ML Governance
export interface CreateMLModelRequest {
  name: string;
  description?: string;
  modelType: string;
  framework: string;
  initialAccuracyScore?: number;
}

export interface UpdateMLModelRequest {
  name?: string;
  description?: string;
  accuracyScore?: number;
}

export interface MakePredictionRequest {
  modelId: string;
  features: Record<string, unknown>;
  includeConfidence?: boolean;
}

export interface SubmitFeedbackRequest {
  predictionId?: string;
  modelId: string;
  feedbackType: string;
  feedbackValue: unknown;
  userId?: string;
  context?: Record<string, unknown>;
}

export interface CreateABNTestRequest {
  name: string;
  description?: string;
  modelAId: string;
  modelBId: string;
  testDurationDays: number;
  trafficSplitPercentage: number;
  successMetric: string;
}
