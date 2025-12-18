/**
 * ACGS-2 TypeScript SDK Utilities
 * Constitutional Hash: cdd01ef066bc6cf2
 */

import { CONSTITUTIONAL_HASH } from '../types';

// =============================================================================
// Constitutional Validation
// =============================================================================

/**
 * Validates that a constitutional hash matches the expected value
 */
export function validateConstitutionalHash(hash: string): boolean {
  return hash === CONSTITUTIONAL_HASH;
}

/**
 * Throws if constitutional hash doesn't match
 */
export function assertConstitutionalHash(hash: string, context?: string): void {
  if (!validateConstitutionalHash(hash)) {
    throw new ConstitutionalHashMismatchError(
      `Constitutional hash mismatch${context ? ` in ${context}` : ''}: expected ${CONSTITUTIONAL_HASH}, got ${hash}`
    );
  }
}

// =============================================================================
// Custom Errors
// =============================================================================

export class ACGS2Error extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly constitutionalHash: string = CONSTITUTIONAL_HASH
  ) {
    super(message);
    this.name = 'ACGS2Error';
  }
}

export class ConstitutionalHashMismatchError extends ACGS2Error {
  constructor(message: string) {
    super(message, 'CONSTITUTIONAL_HASH_MISMATCH');
    this.name = 'ConstitutionalHashMismatchError';
  }
}

export class AuthenticationError extends ACGS2Error {
  constructor(message: string) {
    super(message, 'AUTHENTICATION_ERROR');
    this.name = 'AuthenticationError';
  }
}

export class AuthorizationError extends ACGS2Error {
  constructor(message: string) {
    super(message, 'AUTHORIZATION_ERROR');
    this.name = 'AuthorizationError';
  }
}

export class ValidationError extends ACGS2Error {
  constructor(message: string, public readonly validationErrors?: Record<string, string[]>) {
    super(message, 'VALIDATION_ERROR');
    this.name = 'ValidationError';
  }
}

export class NetworkError extends ACGS2Error {
  constructor(message: string, public readonly statusCode?: number) {
    super(message, 'NETWORK_ERROR');
    this.name = 'NetworkError';
  }
}

export class RateLimitError extends ACGS2Error {
  constructor(
    message: string,
    public readonly retryAfter?: number
  ) {
    super(message, 'RATE_LIMIT_ERROR');
    this.name = 'RateLimitError';
  }
}

export class TimeoutError extends ACGS2Error {
  constructor(message: string) {
    super(message, 'TIMEOUT_ERROR');
    this.name = 'TimeoutError';
  }
}

// =============================================================================
// UUID Generation
// =============================================================================

/**
 * Generates a UUID v4
 */
export function generateUUID(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback for environments without crypto.randomUUID
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

// =============================================================================
// Date/Time Utilities
// =============================================================================

/**
 * Returns current ISO datetime string
 */
export function nowISO(): string {
  return new Date().toISOString();
}

/**
 * Parses ISO datetime string to Date
 */
export function parseISO(dateString: string): Date {
  const date = new Date(dateString);
  if (isNaN(date.getTime())) {
    throw new ValidationError(`Invalid date string: ${dateString}`);
  }
  return date;
}

/**
 * Checks if a date is expired
 */
export function isExpired(expiresAt: string | Date): boolean {
  const expiry = typeof expiresAt === 'string' ? parseISO(expiresAt) : expiresAt;
  return expiry.getTime() < Date.now();
}

// =============================================================================
// Retry Logic
// =============================================================================

export interface RetryOptions {
  maxAttempts: number;
  baseDelay: number;
  maxDelay: number;
  backoffMultiplier: number;
  retryCondition?: (error: unknown) => boolean;
}

const defaultRetryOptions: RetryOptions = {
  maxAttempts: 3,
  baseDelay: 1000,
  maxDelay: 30000,
  backoffMultiplier: 2,
};

/**
 * Executes a function with exponential backoff retry
 */
export async function withRetry<T>(
  fn: () => Promise<T>,
  options: Partial<RetryOptions> = {}
): Promise<T> {
  const opts = { ...defaultRetryOptions, ...options };
  let lastError: unknown;

  for (let attempt = 1; attempt <= opts.maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;

      // Check if we should retry
      if (opts.retryCondition && !opts.retryCondition(error)) {
        throw error;
      }

      // Don't retry on last attempt
      if (attempt === opts.maxAttempts) {
        throw error;
      }

      // Calculate delay with exponential backoff
      const delay = Math.min(
        opts.baseDelay * Math.pow(opts.backoffMultiplier, attempt - 1),
        opts.maxDelay
      );

      // Add jitter (±10%)
      const jitter = delay * 0.1 * (Math.random() * 2 - 1);

      await sleep(delay + jitter);
    }
  }

  throw lastError;
}

/**
 * Sleep for specified milliseconds
 */
export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// =============================================================================
// Object Utilities
// =============================================================================

/**
 * Deep clones an object
 */
export function deepClone<T>(obj: T): T {
  if (obj === null || typeof obj !== 'object') {
    return obj;
  }

  if (obj instanceof Date) {
    return new Date(obj.getTime()) as unknown as T;
  }

  if (Array.isArray(obj)) {
    return obj.map((item) => deepClone(item)) as unknown as T;
  }

  const cloned = {} as T;
  for (const key in obj) {
    if (Object.prototype.hasOwnProperty.call(obj, key)) {
      cloned[key] = deepClone(obj[key]);
    }
  }
  return cloned;
}

/**
 * Deep merges objects
 */
export function deepMerge<T extends Record<string, unknown>>(
  target: T,
  ...sources: Partial<T>[]
): T {
  const result = deepClone(target);

  for (const source of sources) {
    if (!source) continue;

    for (const key in source) {
      if (Object.prototype.hasOwnProperty.call(source, key)) {
        const sourceValue = source[key];
        const targetValue = result[key as keyof T];

        if (
          sourceValue !== null &&
          typeof sourceValue === 'object' &&
          !Array.isArray(sourceValue) &&
          targetValue !== null &&
          typeof targetValue === 'object' &&
          !Array.isArray(targetValue)
        ) {
          (result as Record<string, unknown>)[key] = deepMerge(
            targetValue as Record<string, unknown>,
            sourceValue as Record<string, unknown>
          );
        } else {
          (result as Record<string, unknown>)[key] = deepClone(sourceValue);
        }
      }
    }
  }

  return result;
}

/**
 * Omits specified keys from an object
 */
export function omit<T extends Record<string, unknown>, K extends keyof T>(
  obj: T,
  keys: K[]
): Omit<T, K> {
  const result = { ...obj };
  for (const key of keys) {
    delete result[key];
  }
  return result;
}

/**
 * Picks specified keys from an object
 */
export function pick<T extends Record<string, unknown>, K extends keyof T>(
  obj: T,
  keys: K[]
): Pick<T, K> {
  const result = {} as Pick<T, K>;
  for (const key of keys) {
    if (Object.prototype.hasOwnProperty.call(obj, key)) {
      result[key] = obj[key];
    }
  }
  return result;
}

// =============================================================================
// URL Utilities
// =============================================================================

/**
 * Joins URL parts safely
 */
export function joinUrl(...parts: string[]): string {
  return parts
    .map((part, index) => {
      if (index === 0) {
        return part.replace(/\/+$/, '');
      }
      return part.replace(/^\/+|\/+$/g, '');
    })
    .filter(Boolean)
    .join('/');
}

/**
 * Builds query string from params object
 */
export function buildQueryString(params: Record<string, unknown>): string {
  const searchParams = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) continue;

    if (Array.isArray(value)) {
      for (const item of value) {
        searchParams.append(key, String(item));
      }
    } else {
      searchParams.append(key, String(value));
    }
  }

  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : '';
}

// =============================================================================
// Hashing Utilities
// =============================================================================

/**
 * Creates a simple hash from a string (for non-cryptographic purposes)
 */
export function simpleHash(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  return Math.abs(hash).toString(16).padStart(8, '0');
}

/**
 * Creates a deterministic ID from input data
 */
export function createDeterministicId(data: Record<string, unknown>): string {
  const sortedJson = JSON.stringify(data, Object.keys(data).sort());
  return simpleHash(sortedJson);
}

// =============================================================================
// Type Guards
// =============================================================================

/**
 * Checks if value is a non-null object
 */
export function isObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

/**
 * Checks if value is a non-empty string
 */
export function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.length > 0;
}

/**
 * Checks if value is a valid UUID
 */
export function isUUID(value: unknown): value is string {
  if (typeof value !== 'string') return false;
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  return uuidRegex.test(value);
}

// =============================================================================
// Logging Utilities
// =============================================================================

export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

export interface Logger {
  debug(message: string, ...args: unknown[]): void;
  info(message: string, ...args: unknown[]): void;
  warn(message: string, ...args: unknown[]): void;
  error(message: string, ...args: unknown[]): void;
}

/**
 * Creates a console logger with optional prefix
 */
export function createLogger(prefix: string = 'ACGS2'): Logger {
  const formatMessage = (level: LogLevel, message: string) => {
    const timestamp = new Date().toISOString();
    return `[${timestamp}] [${prefix}] [${level.toUpperCase()}] ${message}`;
  };

  return {
    debug(message: string, ...args: unknown[]) {
      console.debug(formatMessage('debug', message), ...args);
    },
    info(message: string, ...args: unknown[]) {
      console.info(formatMessage('info', message), ...args);
    },
    warn(message: string, ...args: unknown[]) {
      console.warn(formatMessage('warn', message), ...args);
    },
    error(message: string, ...args: unknown[]) {
      console.error(formatMessage('error', message), ...args);
    },
  };
}

/**
 * No-op logger for silent operation
 */
export const silentLogger: Logger = {
  debug: () => {},
  info: () => {},
  warn: () => {},
  error: () => {},
};
