/**
 * Memory Service Tests
 *
 * Unit tests for the Redis-backed memory service using mocks.
 */

import { MemoryService, MemoryEntry } from '../services/memory.js';

// Mock redis client
const mockRedisClient = {
  connect: jest.fn().mockResolvedValue(undefined),
  quit: jest.fn().mockResolvedValue(undefined),
  set: jest.fn().mockResolvedValue('OK'),
  get: jest.fn(),
  del: jest.fn().mockResolvedValue(1),
  exists: jest.fn().mockResolvedValue(1),
  expire: jest.fn().mockResolvedValue(true),
  scan: jest.fn().mockResolvedValue({ cursor: 0, keys: [] }),
  on: jest.fn(),
};

// Mock the redis module
jest.mock('redis', () => ({
  createClient: jest.fn(() => mockRedisClient),
}));

describe('MemoryService', () => {
  let memoryService: MemoryService;

  beforeEach(() => {
    jest.clearAllMocks();
    memoryService = new MemoryService({
      redisUrl: 'redis://localhost:6379',
      defaultTtlSeconds: 3600,
      maxReconnectAttempts: 5,
      keyPrefix: 'test:memory:',
    });
  });

  describe('initialize', () => {
    it('should connect to Redis successfully', async () => {
      const result = await memoryService.initialize();

      expect(result).toBe(true);
      expect(mockRedisClient.connect).toHaveBeenCalled();
      expect(mockRedisClient.on).toHaveBeenCalledWith('error', expect.any(Function));
      expect(mockRedisClient.on).toHaveBeenCalledWith('connect', expect.any(Function));
    });

    it('should return false if connection fails', async () => {
      mockRedisClient.connect.mockRejectedValueOnce(new Error('Connection failed'));

      const result = await memoryService.initialize();

      expect(result).toBe(false);
    });
  });

  describe('set', () => {
    beforeEach(async () => {
      await memoryService.initialize();
    });

    it('should store value with TTL', async () => {
      await memoryService.set('test-key', { foo: 'bar' }, 60);

      expect(mockRedisClient.set).toHaveBeenCalledWith(
        'test:memory:test-key',
        expect.stringContaining('"foo":"bar"'),
        { EX: 60 }
      );
    });

    it('should use default TTL if not specified', async () => {
      await memoryService.set('test-key', { foo: 'bar' });

      expect(mockRedisClient.set).toHaveBeenCalledWith(
        'test:memory:test-key',
        expect.any(String),
        { EX: 3600 }
      );
    });

    it('should throw if client not initialized', async () => {
      const uninitializedService = new MemoryService();

      await expect(uninitializedService.set('key', 'value')).rejects.toThrow(
        'Redis client not initialized'
      );
    });
  });

  describe('get', () => {
    beforeEach(async () => {
      await memoryService.initialize();
    });

    it('should retrieve stored value', async () => {
      const storedEntry: MemoryEntry<{ foo: string }> = {
        value: { foo: 'bar' },
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      mockRedisClient.get.mockResolvedValueOnce(JSON.stringify(storedEntry));

      const result = await memoryService.get<{ foo: string }>('test-key');

      expect(result).toEqual({ foo: 'bar' });
      expect(mockRedisClient.get).toHaveBeenCalledWith('test:memory:test-key');
    });

    it('should return null for non-existent key', async () => {
      mockRedisClient.get.mockResolvedValueOnce(null);

      const result = await memoryService.get('non-existent');

      expect(result).toBeNull();
    });

    it('should return null for corrupted data', async () => {
      mockRedisClient.get.mockResolvedValueOnce('invalid-json');

      const result = await memoryService.get('corrupted-key');

      expect(result).toBeNull();
    });
  });

  describe('delete', () => {
    beforeEach(async () => {
      await memoryService.initialize();
    });

    it('should delete existing key', async () => {
      mockRedisClient.del.mockResolvedValueOnce(1);

      const result = await memoryService.delete('test-key');

      expect(result).toBe(true);
      expect(mockRedisClient.del).toHaveBeenCalledWith('test:memory:test-key');
    });

    it('should return false for non-existent key', async () => {
      mockRedisClient.del.mockResolvedValueOnce(0);

      const result = await memoryService.delete('non-existent');

      expect(result).toBe(false);
    });
  });

  describe('exists', () => {
    beforeEach(async () => {
      await memoryService.initialize();
    });

    it('should return true for existing key', async () => {
      mockRedisClient.exists.mockResolvedValueOnce(1);

      const result = await memoryService.exists('test-key');

      expect(result).toBe(true);
    });

    it('should return false for non-existent key', async () => {
      mockRedisClient.exists.mockResolvedValueOnce(0);

      const result = await memoryService.exists('non-existent');

      expect(result).toBe(false);
    });
  });

  describe('cleanup', () => {
    beforeEach(async () => {
      await memoryService.initialize();
    });

    it('should delete keys matching pattern', async () => {
      mockRedisClient.scan.mockResolvedValueOnce({
        cursor: 0,
        keys: ['test:memory:key1', 'test:memory:key2'],
      });
      mockRedisClient.del.mockResolvedValueOnce(2);

      const result = await memoryService.cleanup('*');

      expect(result).toBe(2);
      expect(mockRedisClient.scan).toHaveBeenCalledWith(0, {
        MATCH: 'test:memory:*',
        COUNT: 100,
      });
    });

    it('should handle multiple scan iterations', async () => {
      mockRedisClient.scan
        .mockResolvedValueOnce({ cursor: 100, keys: ['test:memory:key1'] })
        .mockResolvedValueOnce({ cursor: 0, keys: ['test:memory:key2'] });
      mockRedisClient.del.mockResolvedValue(1);

      const result = await memoryService.cleanup('*');

      expect(result).toBe(2);
      expect(mockRedisClient.scan).toHaveBeenCalledTimes(2);
    });
  });

  describe('disconnect', () => {
    it('should gracefully close connection', async () => {
      await memoryService.initialize();
      await memoryService.disconnect();

      expect(mockRedisClient.quit).toHaveBeenCalled();
      expect(memoryService.isConnected()).toBe(false);
    });
  });

  describe('TLS support', () => {
    it('should configure TLS for rediss:// URLs', async () => {
      const tlsService = new MemoryService({
        redisUrl: 'rediss://redis:6380',
        defaultTtlSeconds: 3600,
        maxReconnectAttempts: 5,
        keyPrefix: 'test:',
      });

      await tlsService.initialize();

      // The TLS configuration is passed to createClient
      const { createClient } = require('redis');
      expect(createClient).toHaveBeenCalledWith(
        expect.objectContaining({
          url: 'rediss://redis:6380',
          socket: expect.objectContaining({
            tls: true,
            rejectUnauthorized: false,
          }),
        })
      );
    });
  });
});
