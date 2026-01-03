/**
 * Memory Service - Redis-backed persistent memory for governance state
 *
 * Implements persistent memory storage that survives service restarts and pod
 * rescheduling. This enables adaptive governance through continuous learning
 * from historical decisions.
 *
 * Features:
 * - Redis-backed storage with automatic reconnection
 * - TTL support for automatic cleanup
 * - Graceful degradation when Redis unavailable
 * - Pattern-based cleanup for batch operations
 *
 * @module services/memory
 */

import { createClient, RedisClientType } from 'redis';
import logger from '../utils/logger.js';

/**
 * Configuration for the memory service
 */
export interface MemoryConfig {
  /** Redis connection URL (supports both redis:// and rediss://) */
  redisUrl: string;
  /** Redis password (optional, for production) */
  redisPassword?: string;
  /** Default TTL in seconds for memory entries (default: 24 hours) */
  defaultTtlSeconds: number;
  /** Maximum reconnection attempts before giving up */
  maxReconnectAttempts: number;
  /** Key prefix for all memory entries */
  keyPrefix: string;
}

/**
 * A memory entry stored in Redis
 */
export interface MemoryEntry<T = unknown> {
  /** The stored value */
  value: T;
  /** Timestamp when the entry was created */
  createdAt: string;
  /** Timestamp when the entry was last updated */
  updatedAt: string;
  /** Optional metadata */
  metadata?: Record<string, unknown>;
}

/**
 * Default configuration values
 */
const DEFAULT_CONFIG: MemoryConfig = {
  redisUrl: process.env.REDIS_URL || 'redis://localhost:6379',
  redisPassword: process.env.REDIS_PASSWORD,
  defaultTtlSeconds: parseInt(process.env.MEMORY_DEFAULT_TTL_SECONDS || '86400', 10),
  maxReconnectAttempts: parseInt(process.env.MEMORY_MAX_RECONNECT_ATTEMPTS || '10', 10),
  keyPrefix: 'claude-flow:memory:',
};

/**
 * Memory Service - Persistent storage backed by Redis
 *
 * Provides CRUD operations for governance state with automatic
 * reconnection and graceful degradation.
 */
export class MemoryService {
  private client: RedisClientType | null = null;
  private config: MemoryConfig;
  private reconnectAttempts = 0;
  private connected = false;

  constructor(config: Partial<MemoryConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * Initialize the Redis connection
   *
   * Supports both development (redis://) and production (rediss://) URLs.
   * TLS is automatically enabled for rediss:// URLs.
   */
  async initialize(): Promise<boolean> {
    const { redisUrl, redisPassword, maxReconnectAttempts } = this.config;
    const isTLS = redisUrl.startsWith('rediss://');

    try {
      this.client = createClient({
        url: redisUrl,
        password: redisPassword,
        socket: {
          reconnectStrategy: (retries) => {
            this.reconnectAttempts = retries;
            if (retries > maxReconnectAttempts) {
              logger.error({ retries }, 'Max Redis reconnection attempts reached');
              return new Error('Max reconnection attempts reached');
            }
            // Exponential backoff with cap
            const delay = Math.min(retries * 50, 500);
            logger.info({ retries, delay }, 'Redis reconnecting...');
            return delay;
          },
          // TLS configuration for production (rediss:// URLs)
          ...(isTLS && {
            tls: true,
            rejectUnauthorized: false, // Allow self-signed certs
          }),
        },
      });

      // Event handlers
      this.client.on('error', (err) => {
        logger.error({ error: err.message }, 'Redis client error');
      });

      this.client.on('connect', () => {
        logger.info('Redis connected');
        this.connected = true;
        this.reconnectAttempts = 0;
      });

      this.client.on('reconnecting', () => {
        logger.info('Redis reconnecting...');
        this.connected = false;
      });

      this.client.on('end', () => {
        logger.info('Redis connection closed');
        this.connected = false;
      });

      // Explicitly connect (required in redis v4+)
      await this.client.connect();

      return true;
    } catch (error) {
      logger.error({ error: (error as Error).message }, 'Failed to initialize Redis connection');
      this.client = null;
      return false;
    }
  }

  /**
   * Check if the service is connected to Redis
   */
  isConnected(): boolean {
    return this.connected && this.client !== null;
  }

  /**
   * Store a value in memory
   *
   * @param key - The key to store the value under
   * @param value - The value to store (will be JSON serialized)
   * @param ttlSeconds - Optional TTL in seconds (uses default if not provided)
   */
  async set<T>(key: string, value: T, ttlSeconds?: number): Promise<void> {
    if (!this.client) {
      throw new Error('Redis client not initialized');
    }

    const fullKey = this.config.keyPrefix + key;
    const entry: MemoryEntry<T> = {
      value,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    const serialized = JSON.stringify(entry);
    const ttl = ttlSeconds ?? this.config.defaultTtlSeconds;

    if (ttl > 0) {
      // Atomic set with expiry
      await this.client.set(fullKey, serialized, { EX: ttl });
    } else {
      await this.client.set(fullKey, serialized);
    }

    logger.debug({ key: fullKey, ttl }, 'Memory entry stored');
  }

  /**
   * Retrieve a value from memory
   *
   * @param key - The key to retrieve
   * @returns The stored value or null if not found
   */
  async get<T>(key: string): Promise<T | null> {
    if (!this.client) {
      throw new Error('Redis client not initialized');
    }

    const fullKey = this.config.keyPrefix + key;
    const data = await this.client.get(fullKey);

    if (!data) {
      return null;
    }

    try {
      const entry: MemoryEntry<T> = JSON.parse(data);
      return entry.value;
    } catch (error) {
      logger.warn({ key: fullKey, error: (error as Error).message }, 'Failed to parse memory entry');
      return null;
    }
  }

  /**
   * Get the full memory entry with metadata
   *
   * @param key - The key to retrieve
   * @returns The full memory entry or null if not found
   */
  async getEntry<T>(key: string): Promise<MemoryEntry<T> | null> {
    if (!this.client) {
      throw new Error('Redis client not initialized');
    }

    const fullKey = this.config.keyPrefix + key;
    const data = await this.client.get(fullKey);

    if (!data) {
      return null;
    }

    try {
      return JSON.parse(data) as MemoryEntry<T>;
    } catch (error) {
      logger.warn({ key: fullKey, error: (error as Error).message }, 'Failed to parse memory entry');
      return null;
    }
  }

  /**
   * Delete a value from memory
   *
   * @param key - The key to delete
   * @returns True if the key was deleted, false if it didn't exist
   */
  async delete(key: string): Promise<boolean> {
    if (!this.client) {
      throw new Error('Redis client not initialized');
    }

    const fullKey = this.config.keyPrefix + key;
    const result = await this.client.del(fullKey);

    logger.debug({ key: fullKey, deleted: result > 0 }, 'Memory entry deleted');
    return result > 0;
  }

  /**
   * Check if a key exists in memory
   *
   * @param key - The key to check
   * @returns True if the key exists
   */
  async exists(key: string): Promise<boolean> {
    if (!this.client) {
      throw new Error('Redis client not initialized');
    }

    const fullKey = this.config.keyPrefix + key;
    const result = await this.client.exists(fullKey);
    return result === 1;
  }

  /**
   * Update the TTL of an existing key
   *
   * @param key - The key to update
   * @param ttlSeconds - New TTL in seconds
   * @returns True if the TTL was updated
   */
  async expire(key: string, ttlSeconds: number): Promise<boolean> {
    if (!this.client) {
      throw new Error('Redis client not initialized');
    }

    const fullKey = this.config.keyPrefix + key;
    const result = await this.client.expire(fullKey, ttlSeconds);
    return result;
  }

  /**
   * Clean up entries matching a pattern using SCAN (non-blocking)
   *
   * @param pattern - Pattern to match (e.g., 'governance:*')
   * @returns Number of keys deleted
   */
  async cleanup(pattern: string = '*'): Promise<number> {
    if (!this.client) {
      throw new Error('Redis client not initialized');
    }

    const fullPattern = this.config.keyPrefix + pattern;
    let cursor = 0;
    let deletedCount = 0;

    // Use SCAN instead of KEYS to avoid blocking
    do {
      const result = await this.client.scan(cursor, {
        MATCH: fullPattern,
        COUNT: 100,
      });

      cursor = result.cursor;
      const keys = result.keys;

      if (keys.length > 0) {
        await this.client.del(keys);
        deletedCount += keys.length;
      }
    } while (cursor !== 0);

    logger.info({ pattern: fullPattern, deletedCount }, 'Memory cleanup completed');
    return deletedCount;
  }

  /**
   * Get all keys matching a pattern
   *
   * @param pattern - Pattern to match
   * @returns Array of matching keys (without prefix)
   */
  async keys(pattern: string = '*'): Promise<string[]> {
    if (!this.client) {
      throw new Error('Redis client not initialized');
    }

    const fullPattern = this.config.keyPrefix + pattern;
    const allKeys: string[] = [];
    let cursor = 0;

    do {
      const result = await this.client.scan(cursor, {
        MATCH: fullPattern,
        COUNT: 100,
      });

      cursor = result.cursor;
      const keys = result.keys.map(k => k.replace(this.config.keyPrefix, ''));
      allKeys.push(...keys);
    } while (cursor !== 0);

    return allKeys;
  }

  /**
   * Gracefully disconnect from Redis
   */
  async disconnect(): Promise<void> {
    if (this.client) {
      await this.client.quit();
      this.client = null;
      this.connected = false;
      logger.info('Redis connection closed gracefully');
    }
  }
}

// Singleton instance for global access
let memoryServiceInstance: MemoryService | null = null;

/**
 * Get the singleton memory service instance
 *
 * @param config - Optional configuration overrides
 * @returns The memory service instance
 */
export function getMemoryService(config?: Partial<MemoryConfig>): MemoryService {
  if (!memoryServiceInstance) {
    memoryServiceInstance = new MemoryService(config);
  }
  return memoryServiceInstance;
}

/**
 * Reset the memory service instance (for testing)
 */
export async function resetMemoryService(): Promise<void> {
  if (memoryServiceInstance) {
    await memoryServiceInstance.disconnect();
    memoryServiceInstance = null;
  }
}

export default MemoryService;
