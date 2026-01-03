/**
 * TypeScript interfaces for memory operations
 *
 * These types define the contract for Redis-backed persistent memory
 * in the claude-flow service for governance state storage.
 */

import type { RedisClientType } from 'redis';

/**
 * Configuration options for the MemoryService
 */
export interface MemoryConfig {
  /** Redis connection URL (redis:// for dev, rediss:// for prod with TLS) */
  url: string;
  /** Optional Redis password for authentication */
  password?: string;
  /** Default TTL in seconds for memory entries (default: 86400 = 24 hours) */
  defaultTtlSeconds?: number;
  /** Maximum reconnection attempts before giving up (default: 10) */
  maxReconnectAttempts?: number;
  /** Whether to enable TLS for secure connections (auto-detected from URL) */
  enableTls?: boolean;
  /** Key prefix for namespacing (e.g., 'governance:acgs-dev:') */
  keyPrefix?: string;
}

/**
 * A stored memory entry with metadata
 */
export interface MemoryEntry<T = unknown> {
  /** The stored value (serialized as JSON in Redis) */
  value: T;
  /** ISO timestamp when the entry was created */
  createdAt: string;
  /** ISO timestamp when the entry was last updated */
  updatedAt: string;
  /** TTL in seconds when entry was set (undefined if no expiry) */
  ttlSeconds?: number;
}

/**
 * Options for memory set operations
 */
export interface MemorySetOptions {
  /** Time-to-live in seconds (uses default if not specified) */
  ttlSeconds?: number;
  /** Whether to update if key already exists (default: true) */
  overwrite?: boolean;
}

/**
 * Result of a memory get operation
 */
export interface MemoryGetResult<T = unknown> {
  /** Whether the key was found */
  found: boolean;
  /** The stored value if found */
  value?: T;
  /** Error message if operation failed */
  error?: string;
}

/**
 * Result of a memory set operation
 */
export interface MemorySetResult {
  /** Whether the operation succeeded */
  success: boolean;
  /** The key that was set */
  key: string;
  /** Error message if operation failed */
  error?: string;
}

/**
 * Result of a memory delete operation
 */
export interface MemoryDeleteResult {
  /** Whether the operation succeeded */
  success: boolean;
  /** Number of keys that were deleted */
  deletedCount: number;
  /** Error message if operation failed */
  error?: string;
}

/**
 * Result of a memory cleanup operation
 */
export interface MemoryCleanupResult {
  /** Whether the cleanup operation completed successfully */
  success: boolean;
  /** Number of keys that were deleted */
  deletedCount: number;
  /** Pattern that was used for cleanup */
  pattern: string;
  /** Time taken in milliseconds */
  durationMs: number;
  /** Error message if operation failed */
  error?: string;
}

/**
 * Connection state of the memory service
 */
export type MemoryConnectionState =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'error';

/**
 * Health status of the memory service
 */
export interface MemoryHealthStatus {
  /** Whether the service is healthy */
  healthy: boolean;
  /** Current connection state */
  connectionState: MemoryConnectionState;
  /** Number of reconnection attempts made */
  reconnectAttempts: number;
  /** ISO timestamp of last successful connection */
  lastConnectedAt?: string;
  /** ISO timestamp of last error */
  lastErrorAt?: string;
  /** Last error message if any */
  lastError?: string;
  /** Latency of last ping in milliseconds */
  latencyMs?: number;
}

/**
 * Events emitted by the memory service
 */
export interface MemoryServiceEvents {
  /** Emitted when connected to Redis */
  connect: () => void;
  /** Emitted when disconnected from Redis */
  disconnect: () => void;
  /** Emitted when reconnecting to Redis */
  reconnecting: () => void;
  /** Emitted when an error occurs */
  error: (error: Error) => void;
  /** Emitted when connection state changes */
  stateChange: (state: MemoryConnectionState) => void;
}

/**
 * Interface for the MemoryService class
 */
export interface IMemoryService {
  /**
   * Initialize the Redis connection
   * @returns Promise that resolves when connected
   * @throws Error if connection fails after max retries
   */
  initialize(): Promise<void>;

  /**
   * Store a value in memory
   * @param key - The key to store under
   * @param value - The value to store (will be JSON serialized)
   * @param options - Optional set options (TTL, overwrite)
   * @returns Result of the set operation
   */
  set<T>(key: string, value: T, options?: MemorySetOptions): Promise<MemorySetResult>;

  /**
   * Retrieve a value from memory
   * @param key - The key to retrieve
   * @returns Result containing the value if found
   */
  get<T>(key: string): Promise<MemoryGetResult<T>>;

  /**
   * Delete a key from memory
   * @param key - The key to delete
   * @returns Result of the delete operation
   */
  delete(key: string): Promise<MemoryDeleteResult>;

  /**
   * Delete multiple keys matching a pattern
   * Uses SCAN for non-blocking iteration
   * @param pattern - Redis glob pattern (e.g., 'governance:*')
   * @returns Result of the cleanup operation
   */
  cleanup(pattern?: string): Promise<MemoryCleanupResult>;

  /**
   * Check if a key exists in memory
   * @param key - The key to check
   * @returns True if key exists
   */
  exists(key: string): Promise<boolean>;

  /**
   * Get the health status of the memory service
   * @returns Current health status
   */
  getHealth(): Promise<MemoryHealthStatus>;

  /**
   * Gracefully disconnect from Redis
   * @returns Promise that resolves when disconnected
   */
  disconnect(): Promise<void>;

  /**
   * Check if the service is connected
   * @returns True if connected
   */
  isConnected(): boolean;
}

/**
 * Options for creating a MemoryService instance
 */
export interface MemoryServiceOptions extends MemoryConfig {
  /** Enable debug logging (default: false) */
  debug?: boolean;
  /** Custom logger function */
  logger?: (message: string, level: 'info' | 'warn' | 'error' | 'debug') => void;
}

/**
 * Type alias for the Redis client type used by MemoryService
 */
export type MemoryRedisClient = RedisClientType;

/**
 * Governance-specific memory key types for type-safe key generation
 */
export interface GovernanceMemoryKeys {
  /** Key for storing governance decisions */
  decision: (tenantId: string, decisionId: string) => string;
  /** Key for storing policy cache */
  policy: (tenantId: string, policyId: string) => string;
  /** Key for storing session state */
  session: (tenantId: string, sessionId: string) => string;
  /** Key for storing agent state */
  agent: (tenantId: string, agentId: string) => string;
}

/**
 * Default governance memory key generators
 */
export const governanceKeys: GovernanceMemoryKeys = {
  decision: (tenantId: string, decisionId: string) =>
    `governance:${tenantId}:decision:${decisionId}`,
  policy: (tenantId: string, policyId: string) =>
    `governance:${tenantId}:policy:${policyId}`,
  session: (tenantId: string, sessionId: string) =>
    `governance:${tenantId}:session:${sessionId}`,
  agent: (tenantId: string, agentId: string) =>
    `governance:${tenantId}:agent:${agentId}`,
};

/**
 * Environment variable names for memory configuration
 */
export const MEMORY_ENV_VARS = {
  REDIS_URL: 'REDIS_URL',
  REDIS_PASSWORD: 'REDIS_PASSWORD',
  MEMORY_DEFAULT_TTL_SECONDS: 'MEMORY_DEFAULT_TTL_SECONDS',
  MEMORY_MAX_RECONNECT_ATTEMPTS: 'MEMORY_MAX_RECONNECT_ATTEMPTS',
  MEMORY_ENABLE_PERSISTENCE: 'MEMORY_ENABLE_PERSISTENCE',
  TENANT_ID: 'TENANT_ID',
} as const;

/**
 * Default values for memory configuration
 */
export const MEMORY_DEFAULTS = {
  /** Default Redis URL for development */
  REDIS_URL: 'redis://localhost:6379',
  /** Default TTL of 24 hours */
  DEFAULT_TTL_SECONDS: 86400,
  /** Default max reconnection attempts */
  MAX_RECONNECT_ATTEMPTS: 10,
  /** Default key prefix */
  KEY_PREFIX: 'governance:',
  /** Default batch size for SCAN operations */
  SCAN_COUNT: 100,
} as const;
