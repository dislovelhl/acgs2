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
