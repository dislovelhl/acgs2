/**
 * Configuration Schema - Zod-based validation with security checks
 *
 * This module provides comprehensive configuration validation with:
 * - Type safety and coercion for environment variables
 * - Security policy enforcement (e.g., no debug in production)
 * - Clear error messages with remediation guidance
 * - RFC 5424 log level compliance
 *
 * @module config/schema
 */

import { z } from "zod";

// ===== Environment Definitions =====

export const environmentSchema = z.enum([
  "development",
  "staging",
  "production",
  "test",
  "ci",
]).describe("Deployment environment");

export const logLevelSchema = z.enum([
  "DEBUG",
  "INFO",
  "WARN",
  "ERROR",
  "CRITICAL",
]).describe("RFC 5424 compliant log level");

// ===== URL Validation Helpers =====

const redisUrlSchema = z.string()
  .refine(
    (url) => url.startsWith("redis://") || url.startsWith("rediss://"),
    { message: "Redis URL must start with redis:// or rediss://" }
  )
  .describe("Redis connection URL (redis:// for dev, rediss:// for TLS)");

const httpUrlSchema = z.string()
  .url()
  .refine(
    (url) => url.startsWith("http://") || url.startsWith("https://"),
    { message: "Must be a valid HTTP/HTTPS URL" }
  );

// ===== Escalation Timeout Schema =====

const timeoutMinutesSchema = z.coerce
  .number()
  .int()
  .min(1, "Timeout must be at least 1 minute")
  .max(1440, "Timeout cannot exceed 24 hours (1440 minutes)")
  .describe("Timeout in minutes (1-1440)");

// ===== Main Configuration Schema =====

export const configSchema = z
  .object({
    // Environment
    ENVIRONMENT: environmentSchema.default("development"),
    TENANT_ID: z.string()
      .min(1, "Tenant ID is required")
      .max(100, "Tenant ID too long")
      .regex(/^[a-zA-Z0-9_-]+$/, "Tenant ID must be alphanumeric with dashes/underscores")
      .default("acgs-dev")
      .describe("Tenant identifier for multi-tenant isolation"),

    // Redis Configuration
    REDIS_URL: redisUrlSchema.default("redis://localhost:6379/0"),
    REDIS_PASSWORD: z.string()
      .optional()
      .describe("Redis authentication password (required in production)"),

    // Kafka Configuration
    KAFKA_BOOTSTRAP: z.string()
      .optional()
      .describe("Kafka bootstrap servers (comma-separated)"),
    KAFKA_PASSWORD: z.string()
      .optional()
      .describe("Kafka authentication password"),

    // Service URLs
    AGENT_BUS_URL: httpUrlSchema.default("http://localhost:8000")
      .describe("Enhanced Agent Bus API URL"),
    OPA_URL: httpUrlSchema.default("http://localhost:8181")
      .describe("Open Policy Agent URL"),
    HITL_APPROVALS_URL: httpUrlSchema.default("http://localhost:8003")
      .describe("HITL Approvals service URL"),

    // Service Ports
    HITL_APPROVALS_PORT: z.coerce
      .number()
      .int()
      .min(1, "Port must be positive")
      .max(65535, "Port must be <= 65535")
      .default(8003)
      .describe("HITL Approvals service port"),

    // Escalation Timeouts
    DEFAULT_ESCALATION_TIMEOUT_MINUTES: timeoutMinutesSchema.default(30)
      .describe("Standard escalation timeout"),
    CRITICAL_ESCALATION_TIMEOUT_MINUTES: timeoutMinutesSchema.default(15)
      .describe("Critical priority escalation timeout"),
    EMERGENCY_ESCALATION_TIMEOUT_MINUTES: timeoutMinutesSchema.default(60)
      .describe("Emergency override timeout"),

    // Logging & Debug
    LOG_LEVEL: logLevelSchema.default("INFO"),
    LOG_FORMAT: z.enum(["json", "text"]).default("json")
      .describe("Log output format"),
    DEBUG: z.coerce.boolean().default(false)
      .describe("Enable debug mode (disabled in production)"),
    RELOAD: z.coerce.boolean().default(false)
      .describe("Enable hot reload"),

    // Security
    CONSTITUTIONAL_HASH: z.string()
      .length(16, "Constitutional hash must be exactly 16 characters")
      .default("cdd01ef066bc6cf2")
      .describe("Constitutional compliance hash"),

    // Memory Service
    MEMORY_DEFAULT_TTL_SECONDS: z.coerce
      .number()
      .int()
      .min(60, "TTL must be at least 60 seconds")
      .max(2592000, "TTL cannot exceed 30 days")
      .default(86400)
      .describe("Default memory entry TTL (24 hours)"),
    MEMORY_MAX_RECONNECT_ATTEMPTS: z.coerce
      .number()
      .int()
      .min(1)
      .max(100)
      .default(10)
      .describe("Maximum Redis reconnection attempts"),
  })

  // ===== Security Policy Refinements =====

  .refine(
    (data) => {
      // Security: DEBUG mode cannot be enabled in production
      if (data.ENVIRONMENT === "production" && data.DEBUG === true) {
        return false;
      }
      return true;
    },
    {
      message: "Security violation: DEBUG mode cannot be enabled in production. Set DEBUG=false in your production .env file.",
      path: ["DEBUG"],
    }
  )
  .refine(
    (data) => {
      // Security: Redis password required in production
      if (data.ENVIRONMENT === "production" && !data.REDIS_PASSWORD) {
        return false;
      }
      return true;
    },
    {
      message: "Security violation: REDIS_PASSWORD is required in production. Set a strong password in your .env file.",
      path: ["REDIS_PASSWORD"],
    }
  )
  .refine(
    (data) => {
      // Security: TLS required for Redis in production
      if (data.ENVIRONMENT === "production" && !data.REDIS_URL.startsWith("rediss://")) {
        return false;
      }
      return true;
    },
    {
      message: "Security violation: Redis TLS (rediss://) is required in production. Update REDIS_URL to use rediss:// protocol.",
      path: ["REDIS_URL"],
    }
  )
  .refine(
    (data) => {
      // Logical: Critical timeout should be shorter than default
      if (data.CRITICAL_ESCALATION_TIMEOUT_MINUTES >= data.DEFAULT_ESCALATION_TIMEOUT_MINUTES) {
        return false;
      }
      return true;
    },
    {
      message: "CRITICAL_ESCALATION_TIMEOUT_MINUTES should be shorter than DEFAULT_ESCALATION_TIMEOUT_MINUTES for proper escalation priority.",
      path: ["CRITICAL_ESCALATION_TIMEOUT_MINUTES"],
    }
  );

export type Config = z.infer<typeof configSchema>;

// ===== Validation Result Types =====

export interface ValidationError {
  field: string;
  message: string;
  code: string;
  remediation?: string;
}

export interface ValidationResult {
  valid: boolean;
  config?: Config;
  errors: ValidationError[];
}
