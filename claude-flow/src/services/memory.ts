/**
 * MemoryService - Redis-backed persistent memory for governance state storage
 *
 * Implements connection management with automatic reconnection,
 * CRUD operations with TTL support, and non-blocking cleanup using SCAN.
 */

import { createClient, RedisClientType } from 'redis';
import {
  IMemoryService,
  MemoryConfig,
  MemoryConnectionState,
  MemoryHealthStatus,
  MemorySetOptions,
  MemorySetResult,
  MemoryGetResult,
  MemoryDeleteResult,
  MemoryCleanupResult,
  MemoryServiceOptions,
  MEMORY_DEFAULTS,
  MEMORY_ENV_VARS,
} from '../types/memory';

/**
 * MemoryService provides Redis-backed persistent memory for governance state.
 *
 * Features:
 * - Automatic TLS detection for redis:// vs rediss:// URLs
 * - Exponential backoff reconnection strategy
 * - Atomic set operations with TTL
 * - Non-blocking cleanup using SCAN (not KEYS)
 * - Graceful degradation when Redis unavailable
 */
export class MemoryService implements IMemoryService {
  private client: RedisClientType | null = null;
  private config: MemoryConfig;
  private connectionState: MemoryConnectionState = 'disconnected';
  private reconnectAttempts = 0;
  private lastConnectedAt?: string;
  private lastErrorAt?: string;
  private lastError?: string;
  private debug: boolean;
  private logger: (message: string, level: 'info' | 'warn' | 'error' | 'debug') => void;

  constructor(options?: MemoryServiceOptions) {
    const redisUrl = options?.url || process.env[MEMORY_ENV_VARS.REDIS_URL] || MEMORY_DEFAULTS.REDIS_URL;

    this.config = {
      url: redisUrl,
      password: options?.password || process.env[MEMORY_ENV_VARS.REDIS_PASSWORD],
      defaultTtlSeconds: options?.defaultTtlSeconds ||
        parseInt(process.env[MEMORY_ENV_VARS.MEMORY_DEFAULT_TTL_SECONDS] || '', 10) ||
        MEMORY_DEFAULTS.DEFAULT_TTL_SECONDS,
      maxReconnectAttempts: options?.maxReconnectAttempts ||
        parseInt(process.env[MEMORY_ENV_VARS.MEMORY_MAX_RECONNECT_ATTEMPTS] || '', 10) ||
        MEMORY_DEFAULTS.MAX_RECONNECT_ATTEMPTS,
      enableTls: options?.enableTls ?? redisUrl.startsWith('rediss://'),
      keyPrefix: options?.keyPrefix || MEMORY_DEFAULTS.KEY_PREFIX,
    };

    this.debug = options?.debug ?? false;
    this.logger = options?.logger ?? this.defaultLogger.bind(this);
  }

  /**
   * Redact sensitive information from log messages
   * Covers: password=xxx, REDIS_PASSWORD=xxx, redis://:password@host, and password in error messages
   */
  private redactSensitiveInfo(message: string): string {
    // Redact password=xxx or password:xxx patterns (case-insensitive)
    message = message.replace(/password[=:]\s*\S+/gi, 'password=[REDACTED]');
    // Redact REDIS_PASSWORD=xxx patterns
    message = message.replace(/REDIS_PASSWORD[=:]\s*\S+/gi, 'REDIS_PASSWORD=[REDACTED]');
    // Redact URL-embedded passwords: redis://:password@host or rediss://:password@host
    message = message.replace(/(rediss?:\/\/):([^@]+)@/gi, '$1:[REDACTED]@');
    // Redact auth password in connection strings
    message = message.replace(/auth\s+\S+/gi, 'auth [REDACTED]');
    return message;
  }

  /**
   * Default logger implementation
   */
  private defaultLogger(message: string, level: 'info' | 'warn' | 'error' | 'debug'): void {
    if (level === 'debug' && !this.debug) return;

    const prefix = `[MemoryService]`;
    switch (level) {
      case 'error':
        // Redact sensitive information from error messages
        message = this.redactSensitiveInfo(message);
        process.stderr.write(`${prefix} ERROR: ${message}\n`);
        break;
      case 'warn':
        // Redact sensitive information from warning messages
        message = this.redactSensitiveInfo(message);
        process.stderr.write(`${prefix} WARN: ${message}\n`);
        break;
      case 'info':
        // Redact sensitive information from info messages (in case of verbose mode)
        message = this.redactSensitiveInfo(message);
        process.stdout.write(`${prefix} ${message}\n`);
        break;
      case 'debug':
        // Redact sensitive information from debug messages (most verbose, highest risk)
        message = this.redactSensitiveInfo(message);
        process.stdout.write(`${prefix} DEBUG: ${message}\n`);
        break;
    }
  }

  /**
   * Update connection state and log the change
   */
  private setConnectionState(state: MemoryConnectionState): void {
    if (this.connectionState !== state) {
      this.connectionState = state;
      this.logger(`Connection state changed to: ${state}`, 'debug');
    }
  }

  /**
   * Initialize the Redis connection
   */
  async initialize(): Promise<void> {
    if (this.client && this.connectionState === 'connected') {
      this.logger('Already connected to Redis', 'debug');
      return;
    }

    this.setConnectionState('connecting');
    const isTls = this.config.enableTls || this.config.url.startsWith('rediss://');
    const maxAttempts = this.config.maxReconnectAttempts || MEMORY_DEFAULTS.MAX_RECONNECT_ATTEMPTS;

    try {
      this.client = createClient({
        url: this.config.url,
        password: this.config.password,
        socket: {
          reconnectStrategy: (retries: number) => {
            this.reconnectAttempts = retries;
            if (retries > maxAttempts) {
              this.setConnectionState('error');
              this.lastError = 'Max reconnection attempts reached';
              this.lastErrorAt = new Date().toISOString();
              return new Error('Max reconnection attempts reached');
            }
            // Exponential backoff: 50ms, 100ms, 150ms... capped at 500ms
            const delay = Math.min(retries * 50, 500);
            this.logger(`Reconnecting in ${delay}ms (attempt ${retries})`, 'debug');
            return delay;
          },
          // TLS configuration for production (rediss:// URLs)
          ...(isTls && {
            tls: true,
            rejectUnauthorized: false, // Allows self-signed certs
          }),
        },
      });

      // Set up event listeners
      this.client.on('error', (err: Error) => {
        this.lastError = err.message;
        this.lastErrorAt = new Date().toISOString();
        this.setConnectionState('error');
        this.logger(`Redis client error: ${err.message}`, 'error');
      });

      this.client.on('connect', () => {
        this.setConnectionState('connected');
        this.lastConnectedAt = new Date().toISOString();
        this.reconnectAttempts = 0;
        this.logger('Redis connected', 'info');
      });

      this.client.on('reconnecting', () => {
        this.setConnectionState('reconnecting');
        this.logger('Redis reconnecting...', 'info');
      });

      this.client.on('end', () => {
        this.setConnectionState('disconnected');
        this.logger('Redis connection closed', 'debug');
      });

      // Explicitly connect (required in redis v4+)
      await this.client.connect();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown connection error';
      this.lastError = errorMessage;
      this.lastErrorAt = new Date().toISOString();
      this.setConnectionState('error');
      this.logger(`Failed to connect to Redis: ${errorMessage}`, 'error');
      throw error;
    }
  }

  /**
   * Check if the service is connected
   */
  isConnected(): boolean {
    return this.client !== null && this.connectionState === 'connected';
  }

  /**
   * Build the full key with optional prefix
   */
  private buildKey(key: string): string {
    // Only add prefix if it's not already there
    if (this.config.keyPrefix && !key.startsWith(this.config.keyPrefix)) {
      return `${this.config.keyPrefix}${key}`;
    }
    return key;
  }

  /**
   * Store a value in memory with optional TTL
   */
  async set<T>(key: string, value: T, options?: MemorySetOptions): Promise<MemorySetResult> {
    if (!this.client || !this.isConnected()) {
      return {
        success: false,
        key,
        error: 'Redis client not initialized or not connected',
      };
    }

    const fullKey = this.buildKey(key);
    const ttlSeconds = options?.ttlSeconds ?? this.config.defaultTtlSeconds;

    try {
      const serialized = JSON.stringify(value);

      if (ttlSeconds && ttlSeconds > 0) {
        // Atomic operation - set with expiry in single command
        await this.client.set(fullKey, serialized, { EX: ttlSeconds });
      } else {
        await this.client.set(fullKey, serialized);
      }

      this.logger(`Set key: ${fullKey}`, 'debug');
      return { success: true, key: fullKey };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      this.logger(`Failed to set key ${fullKey}: ${errorMessage}`, 'error');
      return {
        success: false,
        key: fullKey,
        error: errorMessage,
      };
    }
  }

  /**
   * Retrieve a value from memory
   */
  async get<T>(key: string): Promise<MemoryGetResult<T>> {
    if (!this.client || !this.isConnected()) {
      return {
        found: false,
        error: 'Redis client not initialized or not connected',
      };
    }

    const fullKey = this.buildKey(key);

    try {
      const data = await this.client.get(fullKey);

      if (data === null) {
        return { found: false };
      }

      try {
        const value = JSON.parse(data) as T;
        return { found: true, value };
      } catch (parseError) {
        // Handle malformed JSON - log and return null
        this.logger(`Malformed JSON in key ${fullKey}`, 'warn');
        return {
          found: false,
          error: 'Malformed data in Redis',
        };
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      this.logger(`Failed to get key ${fullKey}: ${errorMessage}`, 'error');
      return {
        found: false,
        error: errorMessage,
      };
    }
  }

  /**
   * Delete a key from memory
   */
  async delete(key: string): Promise<MemoryDeleteResult> {
    if (!this.client || !this.isConnected()) {
      return {
        success: false,
        deletedCount: 0,
        error: 'Redis client not initialized or not connected',
      };
    }

    const fullKey = this.buildKey(key);

    try {
      const deletedCount = await this.client.del(fullKey);
      this.logger(`Deleted key: ${fullKey} (count: ${deletedCount})`, 'debug');
      return {
        success: true,
        deletedCount,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      this.logger(`Failed to delete key ${fullKey}: ${errorMessage}`, 'error');
      return {
        success: false,
        deletedCount: 0,
        error: errorMessage,
      };
    }
  }

  /**
   * Check if a key exists in memory
   */
  async exists(key: string): Promise<boolean> {
    if (!this.client || !this.isConnected()) {
      return false;
    }

    const fullKey = this.buildKey(key);

    try {
      const count = await this.client.exists(fullKey);
      return count > 0;
    } catch (error) {
      this.logger(`Failed to check existence of key ${fullKey}`, 'error');
      return false;
    }
  }

  /**
   * Delete multiple keys matching a pattern using SCAN (non-blocking)
   */
  async cleanup(pattern: string = 'governance:*'): Promise<MemoryCleanupResult> {
    const startTime = Date.now();

    if (!this.client || !this.isConnected()) {
      return {
        success: false,
        deletedCount: 0,
        pattern,
        durationMs: Date.now() - startTime,
        error: 'Redis client not initialized or not connected',
      };
    }

    try {
      let cursor = 0;
      let deletedCount = 0;

      // Use SCAN instead of KEYS to avoid blocking
      do {
        const result = await this.client.scan(cursor, {
          MATCH: pattern,
          COUNT: MEMORY_DEFAULTS.SCAN_COUNT,
        });

        cursor = result.cursor;
        const keys = result.keys;

        if (keys.length > 0) {
          await this.client.del(keys);
          deletedCount += keys.length;
        }
      } while (cursor !== 0);

      this.logger(`Cleanup completed: ${deletedCount} keys deleted matching "${pattern}"`, 'info');

      return {
        success: true,
        deletedCount,
        pattern,
        durationMs: Date.now() - startTime,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      this.logger(`Cleanup failed: ${errorMessage}`, 'error');
      return {
        success: false,
        deletedCount: 0,
        pattern,
        durationMs: Date.now() - startTime,
        error: errorMessage,
      };
    }
  }

  /**
   * Get the health status of the memory service
   */
  async getHealth(): Promise<MemoryHealthStatus> {
    const status: MemoryHealthStatus = {
      healthy: this.isConnected(),
      connectionState: this.connectionState,
      reconnectAttempts: this.reconnectAttempts,
      lastConnectedAt: this.lastConnectedAt,
      lastErrorAt: this.lastErrorAt,
      lastError: this.lastError,
    };

    // Measure latency with PING if connected
    if (this.client && this.isConnected()) {
      try {
        const pingStart = Date.now();
        await this.client.ping();
        status.latencyMs = Date.now() - pingStart;
      } catch {
        status.healthy = false;
      }
    }

    return status;
  }

  /**
   * Gracefully disconnect from Redis
   */
  async disconnect(): Promise<void> {
    if (this.client) {
      try {
        await this.client.quit();
        this.logger('Redis disconnected gracefully', 'info');
      } catch (error) {
        // Force disconnect if quit fails
        this.client.disconnect();
        this.logger('Redis force disconnected', 'warn');
      }
      this.client = null;
      this.setConnectionState('disconnected');
    }
  }
}

/**
 * Singleton instance for shared memory service
 */
let memoryServiceInstance: MemoryService | null = null;

/**
 * Get or create the shared MemoryService instance
 */
export function getMemoryService(options?: MemoryServiceOptions): MemoryService {
  if (!memoryServiceInstance) {
    memoryServiceInstance = new MemoryService(options);
  }
  return memoryServiceInstance;
}

/**
 * Reset the singleton instance (for testing)
 */
export function resetMemoryService(): void {
  if (memoryServiceInstance) {
    memoryServiceInstance.disconnect().catch(() => {});
    memoryServiceInstance = null;
  }
}

// Default export
export default MemoryService;
