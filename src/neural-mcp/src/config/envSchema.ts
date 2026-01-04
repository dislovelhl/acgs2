/**
 * Environment Variable Schema Definitions
 *
 * This module defines Zod schemas for all environment variables used by the ACGS-2 Neural MCP service.
 * All environment variables are validated at application startup to ensure fail-fast behavior.
 *
 * @module envSchema
 */

import { z } from 'zod';

/**
 * Transforms a string to a boolean value.
 * Accepts: 'true', '1', 'yes' for true; 'false', '0', 'no', '' for false.
 */
const booleanTransform = z
  .string()
  .optional()
  .default('false')
  .transform((val) => {
    const lowered = val.toLowerCase().trim();
    return lowered === 'true' || lowered === '1' || lowered === 'yes';
  })
  .describe('Boolean string (true/false, 1/0, yes/no)');

/**
 * Transforms a string to a positive integer with optional default value.
 */
const positiveIntTransform = (defaultValue: number) =>
  z
    .string()
    .optional()
    .default(String(defaultValue))
    .transform((val) => {
      const parsed = parseInt(val, 10);
      if (isNaN(parsed) || parsed < 1) {
        throw new Error(`Expected positive integer, got: ${val}`);
      }
      return parsed;
    });

/**
 * URL schema with optional protocol validation.
 * Accepts redis://, http://, https://, kafka:// protocols.
 */
const urlSchema = (protocols: string[] = ['http', 'https']) =>
  z
    .string()
    .optional()
    .refine(
      (val) => {
        if (!val) return true; // Optional URLs pass if not provided
        try {
          const url = new URL(val);
          const protocol = url.protocol.replace(':', '');
          return protocols.includes(protocol);
        } catch {
          return false;
        }
      },
      (val) => ({
        message: `Invalid URL format. Expected protocols: ${protocols.join(', ')}. Got: ${val}`,
      })
    );

/**
 * Log level enum values.
 */
const LogLevelEnum = z.enum(['DEBUG', 'INFO', 'WARN', 'ERROR']).describe(
  'Logging level: DEBUG for verbose output, INFO for standard, WARN for warnings only, ERROR for errors only'
);

/**
 * Environment enum values.
 */
const EnvironmentEnum = z
  .enum(['development', 'staging', 'production'])
  .describe('Deployment environment: development, staging, or production');

/**
 * Shared environment variable schema for ACGS-2 Neural MCP service.
 *
 * This schema validates all environment variables required for service operation,
 * including infrastructure configuration, timeouts, and logging settings.
 */
export const EnvSchema = z.object({
  // ============================================
  // Environment Configuration
  // ============================================

  /**
   * Tenant identifier for multi-tenancy support.
   * Example: 'acgs-dev', 'acgs-prod'
   */
  TENANT_ID: z
    .string()
    .min(1, 'TENANT_ID is required and cannot be empty')
    .default('acgs-dev')
    .describe('Unique tenant identifier for multi-tenancy support'),

  /**
   * Deployment environment name.
   * Controls security policies and logging verbosity.
   */
  ENVIRONMENT: EnvironmentEnum.default('development'),

  /**
   * Logging level for application output.
   */
  LOG_LEVEL: LogLevelEnum.default('INFO'),

  /**
   * Enable debug mode for verbose logging.
   * WARNING: Must be disabled in production environments.
   */
  DEBUG: booleanTransform,

  /**
   * Enable hot-reload for development.
   * Only effective in development environments.
   */
  RELOAD: booleanTransform,

  // ============================================
  // Infrastructure Configuration
  // ============================================

  /**
   * Redis connection URL.
   * Format: redis://host:port or redis://user:password@host:port
   */
  REDIS_URL: urlSchema(['redis', 'rediss'])
    .default('redis://localhost:6379')
    .describe('Redis connection URL (redis:// or rediss:// for TLS)'),

  /**
   * Redis authentication password.
   * Sensitive: Should be at least 8 characters in production.
   */
  REDIS_PASSWORD: z
    .string()
    .optional()
    .default('')
    .describe('Redis authentication password (sensitive)'),

  /**
   * Kafka bootstrap server address.
   * Format: host:port or kafka://host:port
   */
  KAFKA_BOOTSTRAP: z
    .string()
    .optional()
    .default('')
    .describe('Kafka bootstrap server address (host:port)'),

  /**
   * Kafka authentication password.
   * Sensitive: Required for secured Kafka clusters.
   */
  KAFKA_PASSWORD: z
    .string()
    .optional()
    .default('')
    .describe('Kafka authentication password (sensitive)'),

  /**
   * Agent Bus service URL.
   * Used for inter-agent communication.
   */
  AGENT_BUS_URL: urlSchema(['http', 'https'])
    .default('http://localhost:8000')
    .describe('Agent Bus service URL for inter-agent communication'),

  /**
   * Open Policy Agent (OPA) service URL.
   * Used for policy evaluation and enforcement.
   */
  OPA_URL: urlSchema(['http', 'https'])
    .default('http://localhost:8181')
    .describe('OPA service URL for policy evaluation'),

  /**
   * Human-in-the-Loop (HITL) Approvals service URL.
   */
  HITL_APPROVALS_URL: urlSchema(['http', 'https'])
    .default('http://localhost:8002')
    .describe('HITL Approvals service URL'),

  /**
   * Human-in-the-Loop (HITL) Approvals service port.
   * Must be a valid port number (1-65535).
   */
  HITL_APPROVALS_PORT: z
    .string()
    .optional()
    .default('8002')
    .transform((val) => {
      const port = parseInt(val, 10);
      if (isNaN(port) || port < 1 || port > 65535) {
        throw new Error(`Invalid port number. Must be 1-65535, got: ${val}`);
      }
      return port;
    })
    .describe('HITL Approvals service port (1-65535)'),

  // ============================================
  // Timeout Configuration
  // ============================================

  /**
   * Default timeout for escalation requests in minutes.
   * Used when no specific timeout is configured.
   */
  DEFAULT_ESCALATION_TIMEOUT_MINUTES: positiveIntTransform(30).describe(
    'Default escalation timeout in minutes (default: 30)'
  ),

  /**
   * Timeout for critical escalation requests in minutes.
   * Should be shorter than default for faster response.
   */
  CRITICAL_ESCALATION_TIMEOUT_MINUTES: positiveIntTransform(15).describe(
    'Critical escalation timeout in minutes (default: 15)'
  ),

  /**
   * Timeout for emergency escalation requests in minutes.
   * Used for extended monitoring periods.
   */
  EMERGENCY_ESCALATION_TIMEOUT_MINUTES: positiveIntTransform(60).describe(
    'Emergency escalation timeout in minutes (default: 60)'
  ),
});

/**
 * Type definition for validated environment configuration.
 * Generated from the EnvSchema Zod schema.
 */
export type EnvConfig = z.infer<typeof EnvSchema>;

/**
 * Type definition for raw environment input (before transformation).
 * All values are optional strings as they come from process.env.
 */
export type EnvInput = z.input<typeof EnvSchema>;

/**
 * Schema for validating that required sensitive fields meet security requirements.
 * Applied after base schema validation in production environments.
 */
export const ProductionSecuritySchema = z
  .object({
    REDIS_PASSWORD: z
      .string()
      .min(8, 'REDIS_PASSWORD must be at least 8 characters in production'),
    KAFKA_PASSWORD: z
      .string()
      .min(8, 'KAFKA_PASSWORD must be at least 8 characters in production')
      .optional(),
  })
  .describe('Security requirements for production environment');

/**
 * Export schema for external use and testing.
 */
export default EnvSchema;
