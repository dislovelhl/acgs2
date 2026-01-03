/**
 * Configuration Validator Module
 *
 * This module provides comprehensive configuration validation with:
 * - Zod schema-based validation for all environment variables
 * - Security policy enforcement (e.g., blocking DEBUG mode in production)
 * - Clear error messages with remediation guidance
 * - Fail-fast behavior for invalid configurations
 *
 * @module validator
 */

import { z } from 'zod';
import { EnvSchema, ProductionSecuritySchema, EnvConfig } from './envSchema';

/**
 * Configuration validation error with remediation guidance.
 * Extends Error with structured information about validation failures.
 */
export class ConfigValidationError extends Error {
  public readonly errors: ValidationErrorDetail[];
  public readonly isSecurityViolation: boolean;

  constructor(
    message: string,
    errors: ValidationErrorDetail[],
    isSecurityViolation = false
  ) {
    super(message);
    this.name = 'ConfigValidationError';
    this.errors = errors;
    this.isSecurityViolation = isSecurityViolation;
    Object.setPrototypeOf(this, ConfigValidationError.prototype);
  }
}

/**
 * Detail structure for individual validation errors.
 */
export interface ValidationErrorDetail {
  /** The configuration field that failed validation */
  field: string;
  /** The validation rule that was violated */
  rule: string;
  /** Human-readable description of the error */
  message: string;
  /** Actionable guidance on how to fix the error */
  remediation: string;
  /** The actual value that was provided (sanitized for sensitive fields) */
  providedValue?: string;
}

/**
 * Result type for validation operations.
 */
export interface ValidationResult {
  success: boolean;
  config?: EnvConfig;
  errors?: ValidationErrorDetail[];
}

/**
 * Security policy rules that must be enforced.
 */
interface SecurityPolicy {
  name: string;
  check: (config: EnvConfig) => boolean;
  errorMessage: string;
  remediation: string;
}

/**
 * List of sensitive field names that should not have their values exposed in error messages.
 */
const SENSITIVE_FIELDS = [
  'REDIS_PASSWORD',
  'KAFKA_PASSWORD',
];

/**
 * Security policies to enforce beyond basic schema validation.
 */
const SECURITY_POLICIES: SecurityPolicy[] = [
  {
    name: 'production-debug-mode',
    check: (config) => config.ENVIRONMENT === 'production' && config.DEBUG === true,
    errorMessage: 'DEBUG mode cannot be enabled in production environment',
    remediation:
      'Set DEBUG=false in your production .env file. Debug mode exposes sensitive information and should never be enabled in production.',
  },
  {
    name: 'production-reload-mode',
    check: (config) => config.ENVIRONMENT === 'production' && config.RELOAD === true,
    errorMessage: 'RELOAD mode should not be enabled in production environment',
    remediation:
      'Set RELOAD=false in your production .env file. Hot-reload is intended for development only.',
  },
];

/**
 * Formats a Zod error into a structured validation error detail.
 *
 * @param error - The Zod validation error issue
 * @returns A structured ValidationErrorDetail with remediation guidance
 */
function formatZodError(error: z.ZodIssue): ValidationErrorDetail {
  const field = error.path.join('.') || 'root';
  const isSensitive = SENSITIVE_FIELDS.includes(field);

  // Generate remediation based on error type
  let remediation: string;
  switch (error.code) {
    case 'invalid_type':
      remediation = `Check your .env file and ensure ${field} is set with the correct type. Expected: ${error.expected}, received: ${error.received}.`;
      break;
    case 'invalid_enum_value':
      const options = (error as z.ZodInvalidEnumValueIssue).options?.join(', ') || 'valid values';
      remediation = `Set ${field} to one of the valid options: ${options}.`;
      break;
    case 'too_small':
      remediation = `The value for ${field} is too short or too small. Please provide a value that meets the minimum requirements.`;
      break;
    case 'too_big':
      remediation = `The value for ${field} is too large. Please provide a value within the allowed range.`;
      break;
    case 'invalid_string':
      if ((error as z.ZodInvalidStringIssue).validation === 'url') {
        remediation = `Ensure ${field} contains a valid URL with the correct protocol (e.g., http://, https://, redis://).`;
      } else {
        remediation = `Check the format of ${field} and ensure it meets the required pattern.`;
      }
      break;
    case 'custom':
      remediation = `Review the value for ${field}. ${error.message}`;
      break;
    default:
      remediation = `Check your .env file and ensure ${field} is configured correctly. Refer to the documentation for valid values.`;
  }

  return {
    field,
    rule: error.code,
    message: error.message,
    remediation,
    providedValue: isSensitive ? '[REDACTED]' : undefined,
  };
}

/**
 * Validates environment configuration against the schema and security policies.
 *
 * This function performs comprehensive validation:
 * 1. Schema validation using Zod
 * 2. Security policy checks (e.g., no DEBUG in production)
 * 3. Production-specific password strength requirements
 *
 * @param rawConfig - The raw environment configuration object (typically process.env)
 * @returns The validated and typed configuration object
 * @throws {ConfigValidationError} If validation fails, with detailed error information
 *
 * @example
 * ```typescript
 * try {
 *   const config = validateConfig(process.env);
 *   console.log('Configuration is valid');
 * } catch (error) {
 *   if (error instanceof ConfigValidationError) {
 *     console.error('Validation failed:', error.message);
 *     error.errors.forEach(e => console.error(`- ${e.field}: ${e.remediation}`));
 *   }
 *   process.exit(1);
 * }
 * ```
 */
export function validateConfig(rawConfig: Record<string, unknown>): EnvConfig {
  const result = validateConfigSafe(rawConfig);

  if (!result.success) {
    const errorMessages = result.errors!.map(
      (err) => `  - ${err.field}: ${err.message}\n    Remediation: ${err.remediation}`
    );

    throw new ConfigValidationError(
      `Configuration validation failed:\n\n${errorMessages.join('\n\n')}`,
      result.errors!,
      result.errors!.some((e) => e.rule === 'security_violation')
    );
  }

  return result.config!;
}

/**
 * Validates environment configuration and returns a result object instead of throwing.
 *
 * Use this function when you want to handle validation errors programmatically
 * without exception handling.
 *
 * @param rawConfig - The raw environment configuration object
 * @returns A ValidationResult object with success status and either config or errors
 */
export function validateConfigSafe(rawConfig: Record<string, unknown>): ValidationResult {
  const errors: ValidationErrorDetail[] = [];

  // Step 1: Schema validation with Zod
  const schemaResult = EnvSchema.safeParse(rawConfig);

  if (!schemaResult.success) {
    const zodErrors = schemaResult.error.errors.map(formatZodError);
    errors.push(...zodErrors);
    return { success: false, errors };
  }

  const config = schemaResult.data;

  // Step 2: Security policy checks
  for (const policy of SECURITY_POLICIES) {
    if (policy.check(config)) {
      errors.push({
        field: policy.name,
        rule: 'security_violation',
        message: policy.errorMessage,
        remediation: policy.remediation,
      });
    }
  }

  // Step 3: Production-specific password requirements
  if (config.ENVIRONMENT === 'production') {
    const prodSecurityResult = ProductionSecuritySchema.safeParse({
      REDIS_PASSWORD: config.REDIS_PASSWORD,
      KAFKA_PASSWORD: config.KAFKA_PASSWORD || undefined,
    });

    if (!prodSecurityResult.success) {
      prodSecurityResult.error.errors.forEach((err) => {
        const field = err.path.join('.') || 'unknown';
        errors.push({
          field,
          rule: 'security_violation',
          message: err.message,
          remediation: `In production environments, ${field} must meet security requirements. Use a strong password with at least 8 characters.`,
        });
      });
    }
  }

  if (errors.length > 0) {
    return { success: false, errors };
  }

  return { success: true, config };
}

/**
 * Validates configuration and exits the process if validation fails.
 *
 * This is the recommended function to call at application startup for
 * fail-fast behavior. It will print formatted error messages and exit
 * with code 1 if validation fails.
 *
 * @param rawConfig - The raw environment configuration object
 * @returns The validated configuration if successful
 */
export function validateConfigOrExit(rawConfig: Record<string, unknown>): EnvConfig {
  const result = validateConfigSafe(rawConfig);

  if (!result.success) {
    const isSecurityViolation = result.errors!.some((e) => e.rule === 'security_violation');

    // Format error output for console
    const header = isSecurityViolation
      ? '\n[SECURITY VIOLATION] Configuration validation failed:\n'
      : '\n[ERROR] Configuration validation failed:\n';

    const errorMessages = result.errors!.map((err) => {
      return [
        `  Field: ${err.field}`,
        `  Error: ${err.message}`,
        `  Remediation: ${err.remediation}`,
      ].join('\n');
    });

    // Use process.stderr for error output
    process.stderr.write(header);
    process.stderr.write(errorMessages.join('\n\n'));
    process.stderr.write('\n\nApplication cannot start with invalid configuration.\n');

    process.exit(1);
  }

  return result.config!;
}

/**
 * Creates a partial validator for a subset of configuration fields.
 *
 * Useful for validating specific sections of configuration without
 * requiring all fields to be present.
 *
 * @param fields - Array of field names to validate
 * @returns A validation function for the specified fields
 */
export function createPartialValidator(
  fields: (keyof EnvConfig)[]
): (config: Record<string, unknown>) => ValidationResult {
  return (config: Record<string, unknown>) => {
    const errors: ValidationErrorDetail[] = [];

    // Create a partial schema with only the specified fields
    const partialConfig: Record<string, unknown> = {};
    for (const field of fields) {
      if (field in config) {
        partialConfig[field] = config[field];
      }
    }

    // Validate using the full schema with partial data
    const result = EnvSchema.partial().safeParse(partialConfig);

    if (!result.success) {
      errors.push(...result.error.errors.map(formatZodError));
      return { success: false, errors };
    }

    return { success: true };
  };
}

/**
 * Checks if a specific configuration value is valid without full validation.
 *
 * @param field - The field name to check
 * @param value - The value to validate
 * @returns True if the value is valid for the specified field
 */
export function isValidConfigValue(field: keyof EnvConfig, value: unknown): boolean {
  const testConfig = { [field]: value };
  const result = EnvSchema.partial().safeParse(testConfig);
  return result.success;
}

/**
 * Re-export types for external use.
 */
export type { EnvConfig } from './envSchema';
