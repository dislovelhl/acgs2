import { MemoryService, getMemoryService, resetMemoryService } from '../services/memory';
import { MEMORY_DEFAULTS } from '../types/memory';

// Mock the redis module
jest.mock('redis', () => {
  const mockClient = {
    connect: jest.fn(),
    quit: jest.fn(),
    disconnect: jest.fn(),
    on: jest.fn(),
    get: jest.fn(),
    set: jest.fn(),
    del: jest.fn(),
    exists: jest.fn(),
    scan: jest.fn(),
    ping: jest.fn(),
  };

  return {
    createClient: jest.fn(() => mockClient),
  };
});

// Import the mocked module
import { createClient } from 'redis';

describe('MemoryService', () => {
  let mockClient: ReturnType<typeof createClient>;
  let capturedEventHandlers: Record<string, Function>;

  beforeEach(() => {
    jest.clearAllMocks();
    resetMemoryService();

    // Reset captured event handlers
    capturedEventHandlers = {};

    mockClient = createClient() as any;

    // Capture event handlers when on() is called
    (mockClient.on as jest.Mock).mockImplementation((event: string, handler: Function) => {
      capturedEventHandlers[event] = handler;
      return mockClient;
    });

    // Default successful behaviors
    (mockClient.connect as jest.Mock).mockResolvedValue(undefined);
    (mockClient.quit as jest.Mock).mockResolvedValue(undefined);
    (mockClient.ping as jest.Mock).mockResolvedValue('PONG');
  });

  afterEach(async () => {
    resetMemoryService();
  });

  describe('constructor', () => {
    it('should create instance with default configuration', () => {
      const service = new MemoryService();
      expect(service).toBeInstanceOf(MemoryService);
      expect(service.isConnected()).toBe(false);
    });

    it('should accept custom configuration options', () => {
      const service = new MemoryService({
        url: 'redis://custom-host:6380',
        password: 'test-password',
        defaultTtlSeconds: 3600,
        maxReconnectAttempts: 5,
        keyPrefix: 'test:',
        debug: true,
      });
      expect(service).toBeInstanceOf(MemoryService);
    });

    it('should detect TLS from rediss:// URL', () => {
      const service = new MemoryService({
        url: 'rediss://secure-host:6379',
      });
      expect(service).toBeInstanceOf(MemoryService);
    });
  });

  describe('initialize', () => {
    it('should connect to Redis successfully', async () => {
      const service = new MemoryService();

      // Simulate successful connection
      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        // Trigger connect event
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });

      await service.initialize();

      expect(createClient).toHaveBeenCalled();
      expect(mockClient.connect).toHaveBeenCalled();
      expect(mockClient.on).toHaveBeenCalledWith('error', expect.any(Function));
      expect(mockClient.on).toHaveBeenCalledWith('connect', expect.any(Function));
      expect(mockClient.on).toHaveBeenCalledWith('reconnecting', expect.any(Function));
      expect(mockClient.on).toHaveBeenCalledWith('end', expect.any(Function));
    });

    it('should handle connection failure', async () => {
      const service = new MemoryService();
      const connectionError = new Error('Connection refused');

      (mockClient.connect as jest.Mock).mockRejectedValue(connectionError);

      await expect(service.initialize()).rejects.toThrow('Connection refused');
      expect(service.isConnected()).toBe(false);
    });

    it('should not reinitialize if already connected', async () => {
      const service = new MemoryService();

      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });

      await service.initialize();
      await service.initialize(); // Second call should be no-op

      // connect should only be called once
      expect(mockClient.connect).toHaveBeenCalledTimes(1);
    });
  });

  describe('set', () => {
    let service: MemoryService;

    beforeEach(async () => {
      service = new MemoryService({ keyPrefix: 'test:' });
      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });
      await service.initialize();
    });

    it('should set a value with default TTL', async () => {
      (mockClient.set as jest.Mock).mockResolvedValue('OK');

      const result = await service.set('mykey', { data: 'test' });

      expect(result.success).toBe(true);
      expect(result.key).toBe('test:mykey');
      expect(mockClient.set).toHaveBeenCalledWith(
        'test:mykey',
        JSON.stringify({ data: 'test' }),
        { EX: MEMORY_DEFAULTS.DEFAULT_TTL_SECONDS }
      );
    });

    it('should set a value with custom TTL', async () => {
      (mockClient.set as jest.Mock).mockResolvedValue('OK');

      const result = await service.set('mykey', 'value', { ttlSeconds: 3600 });

      expect(result.success).toBe(true);
      expect(mockClient.set).toHaveBeenCalledWith(
        'test:mykey',
        JSON.stringify('value'),
        { EX: 3600 }
      );
    });

    it('should set a value without TTL when ttlSeconds is 0', async () => {
      (mockClient.set as jest.Mock).mockResolvedValue('OK');

      const result = await service.set('mykey', 'value', { ttlSeconds: 0 });

      expect(result.success).toBe(true);
      expect(mockClient.set).toHaveBeenCalledWith(
        'test:mykey',
        JSON.stringify('value')
      );
    });

    it('should return error when not connected', async () => {
      const disconnectedService = new MemoryService();

      const result = await disconnectedService.set('mykey', 'value');

      expect(result.success).toBe(false);
      expect(result.error).toContain('not initialized');
    });

    it('should handle set errors gracefully', async () => {
      (mockClient.set as jest.Mock).mockRejectedValue(new Error('Redis error'));

      const result = await service.set('mykey', 'value');

      expect(result.success).toBe(false);
      expect(result.error).toBe('Redis error');
    });

    it('should serialize complex objects to JSON', async () => {
      (mockClient.set as jest.Mock).mockResolvedValue('OK');
      const complexObject = {
        nested: { data: [1, 2, 3] },
        date: '2024-01-01',
      };

      const result = await service.set('complex', complexObject);

      expect(result.success).toBe(true);
      expect(mockClient.set).toHaveBeenCalledWith(
        'test:complex',
        JSON.stringify(complexObject),
        expect.anything()
      );
    });
  });

  describe('get', () => {
    let service: MemoryService;

    beforeEach(async () => {
      service = new MemoryService({ keyPrefix: 'test:' });
      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });
      await service.initialize();
    });

    it('should get a value successfully', async () => {
      const storedValue = { data: 'test' };
      (mockClient.get as jest.Mock).mockResolvedValue(JSON.stringify(storedValue));

      const result = await service.get<typeof storedValue>('mykey');

      expect(result.found).toBe(true);
      expect(result.value).toEqual(storedValue);
      expect(mockClient.get).toHaveBeenCalledWith('test:mykey');
    });

    it('should return found: false for non-existent key', async () => {
      (mockClient.get as jest.Mock).mockResolvedValue(null);

      const result = await service.get('nonexistent');

      expect(result.found).toBe(false);
      expect(result.value).toBeUndefined();
    });

    it('should return error when not connected', async () => {
      const disconnectedService = new MemoryService();

      const result = await disconnectedService.get('mykey');

      expect(result.found).toBe(false);
      expect(result.error).toContain('not initialized');
    });

    it('should handle malformed JSON gracefully', async () => {
      (mockClient.get as jest.Mock).mockResolvedValue('not valid json{');

      const result = await service.get('badkey');

      expect(result.found).toBe(false);
      expect(result.error).toBe('Malformed data in Redis');
    });

    it('should handle get errors gracefully', async () => {
      (mockClient.get as jest.Mock).mockRejectedValue(new Error('Redis error'));

      const result = await service.get('mykey');

      expect(result.found).toBe(false);
      expect(result.error).toBe('Redis error');
    });
  });

  describe('delete', () => {
    let service: MemoryService;

    beforeEach(async () => {
      service = new MemoryService({ keyPrefix: 'test:' });
      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });
      await service.initialize();
    });

    it('should delete a key successfully', async () => {
      (mockClient.del as jest.Mock).mockResolvedValue(1);

      const result = await service.delete('mykey');

      expect(result.success).toBe(true);
      expect(result.deletedCount).toBe(1);
      expect(mockClient.del).toHaveBeenCalledWith('test:mykey');
    });

    it('should report 0 deleted for non-existent key', async () => {
      (mockClient.del as jest.Mock).mockResolvedValue(0);

      const result = await service.delete('nonexistent');

      expect(result.success).toBe(true);
      expect(result.deletedCount).toBe(0);
    });

    it('should return error when not connected', async () => {
      const disconnectedService = new MemoryService();

      const result = await disconnectedService.delete('mykey');

      expect(result.success).toBe(false);
      expect(result.deletedCount).toBe(0);
      expect(result.error).toContain('not initialized');
    });

    it('should handle delete errors gracefully', async () => {
      (mockClient.del as jest.Mock).mockRejectedValue(new Error('Redis error'));

      const result = await service.delete('mykey');

      expect(result.success).toBe(false);
      expect(result.error).toBe('Redis error');
    });
  });

  describe('exists', () => {
    let service: MemoryService;

    beforeEach(async () => {
      service = new MemoryService({ keyPrefix: 'test:' });
      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });
      await service.initialize();
    });

    it('should return true for existing key', async () => {
      (mockClient.exists as jest.Mock).mockResolvedValue(1);

      const result = await service.exists('mykey');

      expect(result).toBe(true);
      expect(mockClient.exists).toHaveBeenCalledWith('test:mykey');
    });

    it('should return false for non-existent key', async () => {
      (mockClient.exists as jest.Mock).mockResolvedValue(0);

      const result = await service.exists('nonexistent');

      expect(result).toBe(false);
    });

    it('should return false when not connected', async () => {
      const disconnectedService = new MemoryService();

      const result = await disconnectedService.exists('mykey');

      expect(result).toBe(false);
    });

    it('should return false on error', async () => {
      (mockClient.exists as jest.Mock).mockRejectedValue(new Error('Redis error'));

      const result = await service.exists('mykey');

      expect(result).toBe(false);
    });
  });

  describe('cleanup', () => {
    let service: MemoryService;

    beforeEach(async () => {
      service = new MemoryService({ keyPrefix: 'test:' });
      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });
      await service.initialize();
    });

    it('should cleanup keys matching pattern using SCAN', async () => {
      // Simulate SCAN returning keys then completing
      (mockClient.scan as jest.Mock)
        .mockResolvedValueOnce({ cursor: 0, keys: ['key1', 'key2', 'key3'] });
      (mockClient.del as jest.Mock).mockResolvedValue(3);

      const result = await service.cleanup('governance:*');

      expect(result.success).toBe(true);
      expect(result.deletedCount).toBe(3);
      expect(result.pattern).toBe('governance:*');
      expect(result.durationMs).toBeGreaterThanOrEqual(0);
      expect(mockClient.scan).toHaveBeenCalledWith(0, {
        MATCH: 'governance:*',
        COUNT: MEMORY_DEFAULTS.SCAN_COUNT,
      });
    });

    it('should handle multi-page SCAN results', async () => {
      // First SCAN returns cursor != 0, second returns cursor = 0
      (mockClient.scan as jest.Mock)
        .mockResolvedValueOnce({ cursor: 100, keys: ['key1', 'key2'] })
        .mockResolvedValueOnce({ cursor: 0, keys: ['key3'] });
      (mockClient.del as jest.Mock).mockResolvedValue(2).mockResolvedValue(1);

      const result = await service.cleanup('governance:*');

      expect(result.success).toBe(true);
      expect(result.deletedCount).toBe(3);
      expect(mockClient.scan).toHaveBeenCalledTimes(2);
    });

    it('should handle empty SCAN results', async () => {
      (mockClient.scan as jest.Mock).mockResolvedValue({ cursor: 0, keys: [] });

      const result = await service.cleanup('nonexistent:*');

      expect(result.success).toBe(true);
      expect(result.deletedCount).toBe(0);
    });

    it('should return error when not connected', async () => {
      const disconnectedService = new MemoryService();

      const result = await disconnectedService.cleanup('governance:*');

      expect(result.success).toBe(false);
      expect(result.error).toContain('not initialized');
    });

    it('should handle cleanup errors gracefully', async () => {
      (mockClient.scan as jest.Mock).mockRejectedValue(new Error('Redis error'));

      const result = await service.cleanup('governance:*');

      expect(result.success).toBe(false);
      expect(result.error).toBe('Redis error');
    });

    it('should use default pattern when not specified', async () => {
      (mockClient.scan as jest.Mock).mockResolvedValue({ cursor: 0, keys: [] });

      const result = await service.cleanup();

      expect(result.pattern).toBe('governance:*');
    });
  });

  describe('getHealth', () => {
    let service: MemoryService;

    beforeEach(async () => {
      service = new MemoryService();
      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });
    });

    it('should return healthy status when connected', async () => {
      await service.initialize();
      (mockClient.ping as jest.Mock).mockResolvedValue('PONG');

      const health = await service.getHealth();

      expect(health.healthy).toBe(true);
      expect(health.connectionState).toBe('connected');
      expect(health.reconnectAttempts).toBe(0);
      expect(health.latencyMs).toBeGreaterThanOrEqual(0);
    });

    it('should return unhealthy status when disconnected', async () => {
      const health = await service.getHealth();

      expect(health.healthy).toBe(false);
      expect(health.connectionState).toBe('disconnected');
    });

    it('should handle ping failure gracefully', async () => {
      await service.initialize();
      (mockClient.ping as jest.Mock).mockRejectedValue(new Error('Ping failed'));

      const health = await service.getHealth();

      expect(health.healthy).toBe(false);
    });
  });

  describe('disconnect', () => {
    it('should disconnect gracefully with quit', async () => {
      const service = new MemoryService();
      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });
      await service.initialize();

      await service.disconnect();

      expect(mockClient.quit).toHaveBeenCalled();
      expect(service.isConnected()).toBe(false);
    });

    it('should force disconnect if quit fails', async () => {
      const service = new MemoryService();
      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });
      await service.initialize();
      (mockClient.quit as jest.Mock).mockRejectedValue(new Error('Quit failed'));

      await service.disconnect();

      expect(mockClient.disconnect).toHaveBeenCalled();
    });

    it('should handle disconnect when not connected', async () => {
      const service = new MemoryService();

      await expect(service.disconnect()).resolves.not.toThrow();
    });
  });

  describe('key prefix handling', () => {
    it('should add prefix to keys', async () => {
      const service = new MemoryService({ keyPrefix: 'myapp:' });
      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });
      await service.initialize();
      (mockClient.get as jest.Mock).mockResolvedValue(null);

      await service.get('testkey');

      expect(mockClient.get).toHaveBeenCalledWith('myapp:testkey');
    });

    it('should not double-prefix keys that already have the prefix', async () => {
      const service = new MemoryService({ keyPrefix: 'myapp:' });
      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });
      await service.initialize();
      (mockClient.get as jest.Mock).mockResolvedValue(null);

      await service.get('myapp:testkey');

      expect(mockClient.get).toHaveBeenCalledWith('myapp:testkey');
    });
  });

  describe('singleton pattern', () => {
    beforeEach(() => {
      resetMemoryService();
    });

    it('should return same instance on multiple calls', () => {
      const instance1 = getMemoryService();
      const instance2 = getMemoryService();

      expect(instance1).toBe(instance2);
    });

    it('should accept options only on first call', () => {
      const instance1 = getMemoryService({ keyPrefix: 'first:' });
      const instance2 = getMemoryService({ keyPrefix: 'second:' });

      // Second options should be ignored
      expect(instance1).toBe(instance2);
    });

    it('should create new instance after reset', () => {
      const instance1 = getMemoryService();
      resetMemoryService();
      const instance2 = getMemoryService();

      expect(instance1).not.toBe(instance2);
    });
  });

  describe('error event handling', () => {
    it('should update state on error events', async () => {
      const service = new MemoryService();
      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });
      await service.initialize();

      // Simulate error event
      if (capturedEventHandlers['error']) {
        capturedEventHandlers['error'](new Error('Connection lost'));
      }

      const health = await service.getHealth();
      expect(health.lastError).toBe('Connection lost');
      expect(health.connectionState).toBe('error');
    });

    it('should handle reconnecting events', async () => {
      const service = new MemoryService();
      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });
      await service.initialize();

      // Simulate reconnecting event
      if (capturedEventHandlers['reconnecting']) {
        capturedEventHandlers['reconnecting']();
      }

      const health = await service.getHealth();
      expect(health.connectionState).toBe('reconnecting');
    });
  });

  describe('custom logger', () => {
    it('should use custom logger when provided', async () => {
      const customLogger = jest.fn();
      const service = new MemoryService({
        logger: customLogger,
        debug: true,
      });

      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });
      await service.initialize();

      expect(customLogger).toHaveBeenCalled();
    });
  });
});

/**
 * Integration tests for Redis connection lifecycle
 * These tests verify complete workflows including connect/disconnect cycles,
 * data persistence across sessions, TTL handling, and TLS configuration.
 */
describe('MemoryService integration', () => {
  let mockClient: ReturnType<typeof createClient>;
  let capturedEventHandlers: Record<string, Function>;
  let storedData: Map<string, { value: string; expireAt?: number }>;

  beforeEach(() => {
    jest.clearAllMocks();
    resetMemoryService();

    // Reset captured event handlers
    capturedEventHandlers = {};

    // Simulated Redis storage for integration tests
    storedData = new Map();

    mockClient = createClient() as any;

    // Capture event handlers when on() is called
    (mockClient.on as jest.Mock).mockImplementation((event: string, handler: Function) => {
      capturedEventHandlers[event] = handler;
      return mockClient;
    });

    // Default successful behaviors
    (mockClient.connect as jest.Mock).mockResolvedValue(undefined);
    (mockClient.quit as jest.Mock).mockResolvedValue(undefined);
    (mockClient.disconnect as jest.Mock).mockResolvedValue(undefined);
    (mockClient.ping as jest.Mock).mockResolvedValue('PONG');

    // Simulate Redis SET with optional TTL
    (mockClient.set as jest.Mock).mockImplementation(
      async (key: string, value: string, options?: { EX?: number }) => {
        const entry: { value: string; expireAt?: number } = { value };
        if (options?.EX) {
          entry.expireAt = Date.now() + options.EX * 1000;
        }
        storedData.set(key, entry);
        return 'OK';
      }
    );

    // Simulate Redis GET with TTL expiration check
    (mockClient.get as jest.Mock).mockImplementation(async (key: string) => {
      const entry = storedData.get(key);
      if (!entry) return null;

      // Check TTL expiration
      if (entry.expireAt && Date.now() > entry.expireAt) {
        storedData.delete(key);
        return null;
      }
      return entry.value;
    });

    // Simulate Redis DEL
    (mockClient.del as jest.Mock).mockImplementation(async (keys: string | string[]) => {
      const keyArray = Array.isArray(keys) ? keys : [keys];
      let deleted = 0;
      for (const key of keyArray) {
        if (storedData.has(key)) {
          storedData.delete(key);
          deleted++;
        }
      }
      return deleted;
    });

    // Simulate Redis EXISTS
    (mockClient.exists as jest.Mock).mockImplementation(async (key: string) => {
      const entry = storedData.get(key);
      if (!entry) return 0;

      // Check TTL expiration
      if (entry.expireAt && Date.now() > entry.expireAt) {
        storedData.delete(key);
        return 0;
      }
      return 1;
    });

    // Simulate Redis SCAN for pattern matching
    (mockClient.scan as jest.Mock).mockImplementation(
      async (_cursor: number, options?: { MATCH?: string; COUNT?: number }) => {
        const pattern = options?.MATCH || '*';
        const regex = new RegExp(
          '^' + pattern.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*').replace(/\?/g, '.') + '$'
        );

        const matchingKeys: string[] = [];
        for (const key of storedData.keys()) {
          if (regex.test(key)) {
            // Check TTL expiration before including
            const entry = storedData.get(key);
            if (entry && (!entry.expireAt || Date.now() <= entry.expireAt)) {
              matchingKeys.push(key);
            }
          }
        }

        return { cursor: 0, keys: matchingKeys };
      }
    );
  });

  afterEach(async () => {
    resetMemoryService();
    storedData.clear();
  });

  describe('integration: connection lifecycle', () => {
    it('should complete full connection lifecycle: connect -> operations -> disconnect', async () => {
      const service = new MemoryService({ keyPrefix: 'test:' });

      // Phase 1: Connect
      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });

      await service.initialize();
      expect(service.isConnected()).toBe(true);

      // Phase 2: Perform operations
      const setResult = await service.set('lifecycle-key', { data: 'test-value' });
      expect(setResult.success).toBe(true);

      const getResult = await service.get<{ data: string }>('lifecycle-key');
      expect(getResult.found).toBe(true);
      expect(getResult.value?.data).toBe('test-value');

      // Phase 3: Disconnect
      await service.disconnect();
      expect(service.isConnected()).toBe(false);
      expect(mockClient.quit).toHaveBeenCalled();
    });

    it('should handle multiple connect/disconnect cycles without errors', async () => {
      const service = new MemoryService({ keyPrefix: 'cycle:' });

      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });

      // Cycle 1
      await service.initialize();
      expect(service.isConnected()).toBe(true);

      await service.set('cycle1-key', 'value1');
      await service.disconnect();
      expect(service.isConnected()).toBe(false);

      // Cycle 2 - service needs to be re-instantiated since disconnect nullifies client
      const service2 = new MemoryService({ keyPrefix: 'cycle:' });
      await service2.initialize();
      expect(service2.isConnected()).toBe(true);

      // Data from previous cycle should still exist in storage
      const result = await service2.get<string>('cycle1-key');
      expect(result.found).toBe(true);
      expect(result.value).toBe('value1');

      await service2.disconnect();
      expect(service2.isConnected()).toBe(false);
    });

    it('should handle disconnect when quit fails by forcing disconnect', async () => {
      const service = new MemoryService();

      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });

      await service.initialize();

      // Simulate quit failure
      (mockClient.quit as jest.Mock).mockRejectedValue(new Error('Quit failed'));

      await service.disconnect();

      // Should fall back to force disconnect
      expect(mockClient.disconnect).toHaveBeenCalled();
      expect(service.isConnected()).toBe(false);
    });
  });

  describe('integration: data persistence across restarts', () => {
    it('should persist data across disconnect/reconnect cycle', async () => {
      // Session 1: Write data
      const session1 = new MemoryService({ keyPrefix: 'persist:' });

      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });

      await session1.initialize();

      const testData = { userId: '123', preferences: { theme: 'dark' } };
      await session1.set('user-settings', testData);

      // Verify data was written
      const checkResult = await session1.get<typeof testData>('user-settings');
      expect(checkResult.found).toBe(true);
      expect(checkResult.value).toEqual(testData);

      // Disconnect session 1 (simulating restart)
      await session1.disconnect();

      // Session 2: Reconnect and read data
      const session2 = new MemoryService({ keyPrefix: 'persist:' });
      await session2.initialize();

      // Data should persist across sessions
      const persistedResult = await session2.get<typeof testData>('user-settings');
      expect(persistedResult.found).toBe(true);
      expect(persistedResult.value).toEqual(testData);

      await session2.disconnect();
    });

    it('should persist multiple keys and retrieve them after reconnect', async () => {
      const prefix = 'multi:';
      const session1 = new MemoryService({ keyPrefix: prefix });

      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });

      await session1.initialize();

      // Write multiple keys
      await session1.set('key1', 'value1');
      await session1.set('key2', { nested: 'object' });
      await session1.set('key3', [1, 2, 3]);

      await session1.disconnect();

      // Reconnect
      const session2 = new MemoryService({ keyPrefix: prefix });
      await session2.initialize();

      // Verify all keys persist
      const result1 = await session2.get<string>('key1');
      const result2 = await session2.get<{ nested: string }>('key2');
      const result3 = await session2.get<number[]>('key3');

      expect(result1.value).toBe('value1');
      expect(result2.value).toEqual({ nested: 'object' });
      expect(result3.value).toEqual([1, 2, 3]);

      await session2.disconnect();
    });
  });

  describe('integration: TTL expiration', () => {
    it('should expire keys after TTL elapses', async () => {
      const service = new MemoryService({ keyPrefix: 'ttl:' });

      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });

      await service.initialize();

      // Set key with very short TTL (1 second)
      await service.set('short-lived', 'temporary-data', { ttlSeconds: 1 });

      // Immediately after, key should exist
      const immediateResult = await service.get<string>('short-lived');
      expect(immediateResult.found).toBe(true);
      expect(immediateResult.value).toBe('temporary-data');

      // Wait for TTL to expire
      await new Promise((resolve) => setTimeout(resolve, 1100));

      // After TTL, key should be gone
      const expiredResult = await service.get<string>('short-lived');
      expect(expiredResult.found).toBe(false);

      await service.disconnect();
    });

    it('should handle keys with and without TTL correctly', async () => {
      const service = new MemoryService({ keyPrefix: 'mixed:' });

      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });

      await service.initialize();

      // Set one key with TTL, one without
      await service.set('with-ttl', 'expires-soon', { ttlSeconds: 1 });
      await service.set('no-ttl', 'permanent', { ttlSeconds: 0 });

      // Both should exist initially
      expect((await service.get('with-ttl')).found).toBe(true);
      expect((await service.get('no-ttl')).found).toBe(true);

      // Wait for TTL to expire
      await new Promise((resolve) => setTimeout(resolve, 1100));

      // Only the permanent key should remain
      expect((await service.get('with-ttl')).found).toBe(false);
      expect((await service.get('no-ttl')).found).toBe(true);
      expect((await service.get<string>('no-ttl')).value).toBe('permanent');

      await service.disconnect();
    });

    it('should verify TTL expiration after reconnect', async () => {
      const prefix = 'ttl-reconnect:';

      // Session 1: Set key with TTL
      const session1 = new MemoryService({ keyPrefix: prefix });

      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });

      await session1.initialize();
      await session1.set('expiring-key', 'will-expire', { ttlSeconds: 1 });
      await session1.disconnect();

      // Wait for TTL to expire
      await new Promise((resolve) => setTimeout(resolve, 1100));

      // Session 2: Reconnect and verify key is gone
      const session2 = new MemoryService({ keyPrefix: prefix });
      await session2.initialize();

      const result = await session2.get<string>('expiring-key');
      expect(result.found).toBe(false);

      await session2.disconnect();
    });
  });

  describe('integration: pattern-based cleanup', () => {
    it('should cleanup keys matching pattern and preserve others', async () => {
      const service = new MemoryService({ keyPrefix: '' }); // No prefix for this test

      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });

      await service.initialize();

      // Set up test data with different prefixes
      await service.set('governance:session:123', 'gov-data-1', { ttlSeconds: 0 });
      await service.set('governance:session:456', 'gov-data-2', { ttlSeconds: 0 });
      await service.set('governance:decision:789', 'decision-data', { ttlSeconds: 0 });
      await service.set('cache:user:123', 'cache-data-1', { ttlSeconds: 0 });
      await service.set('cache:user:456', 'cache-data-2', { ttlSeconds: 0 });
      await service.set('config:settings', 'config-data', { ttlSeconds: 0 });

      // All keys should exist
      expect((await service.get('governance:session:123')).found).toBe(true);
      expect((await service.get('cache:user:123')).found).toBe(true);
      expect((await service.get('config:settings')).found).toBe(true);

      // Cleanup only governance keys
      const cleanupResult = await service.cleanup('governance:*');
      expect(cleanupResult.success).toBe(true);
      expect(cleanupResult.deletedCount).toBe(3);
      expect(cleanupResult.pattern).toBe('governance:*');
      expect(cleanupResult.durationMs).toBeGreaterThanOrEqual(0);

      // Governance keys should be gone
      expect((await service.get('governance:session:123')).found).toBe(false);
      expect((await service.get('governance:session:456')).found).toBe(false);
      expect((await service.get('governance:decision:789')).found).toBe(false);

      // Non-governance keys should remain
      expect((await service.get('cache:user:123')).found).toBe(true);
      expect((await service.get('cache:user:456')).found).toBe(true);
      expect((await service.get('config:settings')).found).toBe(true);

      await service.disconnect();
    });

    it('should cleanup with more specific patterns', async () => {
      const service = new MemoryService({ keyPrefix: '' });

      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });

      await service.initialize();

      // Set up test data
      await service.set('governance:session:123', 'session-1', { ttlSeconds: 0 });
      await service.set('governance:session:456', 'session-2', { ttlSeconds: 0 });
      await service.set('governance:decision:789', 'decision-1', { ttlSeconds: 0 });

      // Cleanup only session keys
      const cleanupResult = await service.cleanup('governance:session:*');
      expect(cleanupResult.success).toBe(true);
      expect(cleanupResult.deletedCount).toBe(2);

      // Session keys should be gone
      expect((await service.get('governance:session:123')).found).toBe(false);
      expect((await service.get('governance:session:456')).found).toBe(false);

      // Decision keys should remain
      expect((await service.get('governance:decision:789')).found).toBe(true);

      await service.disconnect();
    });

    it('should return zero deleted count when pattern matches nothing', async () => {
      const service = new MemoryService({ keyPrefix: '' });

      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });

      await service.initialize();

      // Set some data
      await service.set('real-key', 'real-value', { ttlSeconds: 0 });

      // Cleanup with non-matching pattern
      const cleanupResult = await service.cleanup('nonexistent:*');
      expect(cleanupResult.success).toBe(true);
      expect(cleanupResult.deletedCount).toBe(0);

      // Original data should be untouched
      expect((await service.get('real-key')).found).toBe(true);

      await service.disconnect();
    });
  });

  describe('integration: TLS configuration', () => {
    it('should detect TLS from redis:// URL (no TLS)', async () => {
      const service = new MemoryService({
        url: 'redis://localhost:6379',
      });

      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });

      await service.initialize();

      // Verify createClient was called with correct URL (no TLS options)
      const clientConfig = (createClient as jest.Mock).mock.calls[0][0];
      expect(clientConfig.url).toBe('redis://localhost:6379');
      expect(clientConfig.socket?.tls).toBeUndefined();

      await service.disconnect();
    });

    it('should detect TLS from rediss:// URL and configure TLS', async () => {
      const service = new MemoryService({
        url: 'rediss://secure-redis:6380',
        password: 'test-password',
      });

      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });

      await service.initialize();

      // Verify createClient was called with TLS configuration
      const clientConfig = (createClient as jest.Mock).mock.calls[0][0];
      expect(clientConfig.url).toBe('rediss://secure-redis:6380');
      expect(clientConfig.password).toBe('test-password');
      expect(clientConfig.socket?.tls).toBe(true);
      expect(clientConfig.socket?.rejectUnauthorized).toBe(false);

      await service.disconnect();
    });

    it('should allow explicit TLS override via enableTls option', async () => {
      // Force TLS even with redis:// URL (for testing)
      const service = new MemoryService({
        url: 'redis://localhost:6379',
        enableTls: true,
      });

      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });

      await service.initialize();

      // Verify TLS was enabled despite redis:// URL
      const clientConfig = (createClient as jest.Mock).mock.calls[0][0];
      expect(clientConfig.socket?.tls).toBe(true);

      await service.disconnect();
    });
  });

  describe('integration: reconnection handling', () => {
    it('should handle connection error and track error state', async () => {
      const service = new MemoryService();

      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });

      await service.initialize();
      expect(service.isConnected()).toBe(true);

      // Simulate error event (connection lost)
      if (capturedEventHandlers['error']) {
        capturedEventHandlers['error'](new Error('Connection lost'));
      }

      // Health should reflect error state
      const health = await service.getHealth();
      expect(health.connectionState).toBe('error');
      expect(health.lastError).toBe('Connection lost');
      expect(health.lastErrorAt).toBeDefined();

      await service.disconnect();
    });

    it('should track reconnection state during reconnect attempts', async () => {
      const service = new MemoryService();

      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });

      await service.initialize();

      // Simulate reconnecting event
      if (capturedEventHandlers['reconnecting']) {
        capturedEventHandlers['reconnecting']();
      }

      const health = await service.getHealth();
      expect(health.connectionState).toBe('reconnecting');

      // Simulate successful reconnect
      if (capturedEventHandlers['connect']) {
        capturedEventHandlers['connect']();
      }

      const healthAfterReconnect = await service.getHealth();
      expect(healthAfterReconnect.connectionState).toBe('connected');
      expect(healthAfterReconnect.reconnectAttempts).toBe(0);

      await service.disconnect();
    });

    it('should resume operations after reconnection', async () => {
      const service = new MemoryService({ keyPrefix: 'reconnect:' });

      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });

      await service.initialize();

      // Store data before simulated disconnect
      await service.set('before-disconnect', 'preserved-data');

      // Simulate error -> reconnecting -> connect cycle
      if (capturedEventHandlers['error']) {
        capturedEventHandlers['error'](new Error('Temporary disconnect'));
      }
      if (capturedEventHandlers['reconnecting']) {
        capturedEventHandlers['reconnecting']();
      }
      if (capturedEventHandlers['connect']) {
        capturedEventHandlers['connect']();
      }

      // Operations should work after reconnection
      const result = await service.get<string>('before-disconnect');
      expect(result.found).toBe(true);
      expect(result.value).toBe('preserved-data');

      await service.disconnect();
    });
  });

  describe('integration: health monitoring', () => {
    it('should provide accurate health status throughout lifecycle', async () => {
      const service = new MemoryService();

      // Before connection
      const healthBefore = await service.getHealth();
      expect(healthBefore.healthy).toBe(false);
      expect(healthBefore.connectionState).toBe('disconnected');

      // Connect
      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });

      await service.initialize();

      // After connection
      const healthAfter = await service.getHealth();
      expect(healthAfter.healthy).toBe(true);
      expect(healthAfter.connectionState).toBe('connected');
      expect(healthAfter.latencyMs).toBeGreaterThanOrEqual(0);
      expect(healthAfter.lastConnectedAt).toBeDefined();

      // After error
      if (capturedEventHandlers['error']) {
        capturedEventHandlers['error'](new Error('Test error'));
      }

      const healthAfterError = await service.getHealth();
      expect(healthAfterError.connectionState).toBe('error');
      expect(healthAfterError.lastError).toBe('Test error');

      // After disconnect
      await service.disconnect();

      const healthAfterDisconnect = await service.getHealth();
      expect(healthAfterDisconnect.connectionState).toBe('disconnected');
    });

    it('should measure latency correctly via PING', async () => {
      const service = new MemoryService();

      (mockClient.connect as jest.Mock).mockImplementation(async () => {
        if (capturedEventHandlers['connect']) {
          capturedEventHandlers['connect']();
        }
      });

      // Simulate a PING with 5ms delay
      (mockClient.ping as jest.Mock).mockImplementation(async () => {
        await new Promise((resolve) => setTimeout(resolve, 5));
        return 'PONG';
      });

      await service.initialize();

      const health = await service.getHealth();
      expect(health.healthy).toBe(true);
      expect(health.latencyMs).toBeGreaterThanOrEqual(5);
      expect(health.latencyMs).toBeLessThan(100); // Sanity check

      await service.disconnect();
    });
  });
});
