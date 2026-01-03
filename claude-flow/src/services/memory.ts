import { createClient, RedisClientType } from 'redis';
import { MemoryConfig, MemoryEntry, MemorySearchResult } from '../types/memory';
import { logger } from '../utils/logger';

export class MemoryService {
  private client: RedisClientType | null = null;
  private readonly config: MemoryConfig;

  constructor(config?: Partial<MemoryConfig>) {
    this.config = {
      url: process.env.REDIS_URL || 'redis://localhost:6379',
      password: process.env.REDIS_PASSWORD,
      defaultTtlSeconds: parseInt(process.env.MEMORY_DEFAULT_TTL_SECONDS || '86400', 10),
      maxReconnectAttempts: parseInt(process.env.MEMORY_MAX_RECONNECT_ATTEMPTS || '10', 10),
      ...config,
    };
  }

  /**
   * Initialize Redis connection
   */
  async initialize(): Promise<void> {
    const isTLS = this.config.url.startsWith('rediss://');

    this.client = createClient({
      url: this.config.url,
      password: this.config.password,
      socket: {
        reconnectStrategy: (retries) => {
          if (retries > (this.config.maxReconnectAttempts || 10)) {
            logger.error('Max Redis reconnection attempts reached');
            return new Error('Max reconnection attempts reached');
          }
          const delay = Math.min(retries * 50, 500);
          return delay;
        },
        ...(isTLS && {
          tls: true,
          rejectUnauthorized: false, // Allows self-signed certs
        }),
      },
    });

    this.client.on('error', (err) => logger.error('Redis Client Error', err));
    this.client.on('connect', () => logger.info('Redis connected'));
    this.client.on('reconnecting', () => logger.info('Redis reconnecting...'));
    this.client.on('ready', () => logger.info('Redis client ready'));

    try {
      await this.client.connect();
    } catch (err) {
      logger.error('Failed to connect to Redis', err);
      // Don't throw, allow degraded operation
    }
  }

  /**
   * Set a value in memory with optional TTL
   */
  async set(key: string, value: any, ttlSeconds?: number): Promise<void> {
    if (!this.client || !this.client.isOpen) {
      logger.warn('Redis client not connected, skipping set operation');
      return;
    }

    try {
      const serialized = JSON.stringify(value);
      const ttl = ttlSeconds !== undefined ? ttlSeconds : this.config.defaultTtlSeconds;

      if (ttl && ttl > 0) {
        await this.client.set(key, serialized, { EX: ttl });
      } else {
        await this.client.set(key, serialized);
      }
    } catch (err) {
      logger.error(`Error setting key ${key} in Redis`, err);
    }
  }

  /**
   * Get a value from memory
   */
  async get<T = any>(key: string): Promise<T | null> {
    if (!this.client || !this.client.isOpen) {
      logger.warn('Redis client not connected, skipping get operation');
      return null;
    }

    try {
      const value = await this.client.get(key);
      if (!value) return null;

      return JSON.parse(value) as T;
    } catch (err) {
      logger.error(`Error getting key ${key} from Redis`, err);
      return null;
    }
  }

  /**
   * Delete a value from memory
   */
  async delete(key: string): Promise<void> {
    if (!this.client || !this.client.isOpen) {
      logger.warn('Redis client not connected, skipping delete operation');
      return;
    }

    try {
      await this.client.del(key);
    } catch (err) {
      logger.error(`Error deleting key ${key} from Redis`, err);
    }
  }

  /**
   * Cleanup keys matching a pattern
   */
  async cleanup(pattern: string = 'governance:*'): Promise<number> {
    if (!this.client || !this.client.isOpen) {
      logger.warn('Redis client not connected, skipping cleanup operation');
      return 0;
    }

    let cursor = 0;
    let deletedCount = 0;

    try {
      do {
        const result = await this.client.scan(cursor, {
          MATCH: pattern,
          COUNT: 100,
        });

        cursor = result.cursor;
        const keys = result.keys;

        if (keys.length > 0) {
          await this.client.del(keys);
          deletedCount += keys.length;
        }
      } while (cursor !== 0);

      logger.info(`Cleaned up ${deletedCount} keys matching pattern ${pattern}`);
      return deletedCount;
    } catch (err) {
      logger.error(`Error during cleanup with pattern ${pattern}`, err);
      return deletedCount;
    }
  }

  /**
   * Disconnect from Redis
   */
  async disconnect(): Promise<void> {
    if (this.client) {
      try {
        await this.client.quit();
        logger.info('Redis client disconnected gracefully');
      } catch (err) {
        logger.error('Error during Redis disconnect', err);
      }
    }
  }
}

// Export singleton instance
export const memoryService = new MemoryService();
