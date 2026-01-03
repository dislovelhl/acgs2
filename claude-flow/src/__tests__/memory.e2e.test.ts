/**
 * End-to-End Tests for MemoryService Data Persistence
 *
 * These tests verify the core requirement: state survives service restarts.
 *
 * Test Strategy:
 * - Tests use mocked Redis for CI/automated testing
 * - For real E2E verification, set RUN_REAL_REDIS_TESTS=true and ensure Redis is running
 *
 * Manual E2E Verification Steps:
 * 1. Start Redis container: docker run -d --name redis-e2e -p 6379:6379 redis:7-alpine
 * 2. Run tests: RUN_REAL_REDIS_TESTS=true npm test -- memory.e2e.test.ts
 * 3. Stop container: docker stop redis-e2e && docker rm redis-e2e
 */

import { MemoryService, resetMemoryService } from '../services/memory';

// Check if we should use real Redis
const USE_REAL_REDIS = process.env.RUN_REAL_REDIS_TESTS === 'true';

// Mock the redis module for non-real tests
if (!USE_REAL_REDIS) {
  jest.mock('redis', () => {
    // Shared storage to persist data across service restarts
    const persistentStorage = new Map<string, { value: string; expireAt?: number }>();

    const createMockClient = () => {
      const eventHandlers: Record<string, Function> = {};

      return {
        connect: jest.fn(async function (this: any) {
          // Simulate successful connection
          if (eventHandlers['connect']) {
            eventHandlers['connect']();
          }
        }),
        quit: jest.fn().mockResolvedValue(undefined),
        disconnect: jest.fn().mockResolvedValue(undefined),
        ping: jest.fn().mockResolvedValue('PONG'),
        on: jest.fn((event: string, handler: Function) => {
          eventHandlers[event] = handler;
          return createMockClient();
        }),
        set: jest.fn(async (key: string, value: string, options?: { EX?: number }) => {
          const entry: { value: string; expireAt?: number } = { value };
          if (options?.EX) {
            entry.expireAt = Date.now() + options.EX * 1000;
          }
          persistentStorage.set(key, entry);
          return 'OK';
        }),
        get: jest.fn(async (key: string) => {
          const entry = persistentStorage.get(key);
          if (!entry) return null;

          // Check TTL expiration
          if (entry.expireAt && Date.now() > entry.expireAt) {
            persistentStorage.delete(key);
            return null;
          }
          return entry.value;
        }),
        del: jest.fn(async (keys: string | string[]) => {
          const keyArray = Array.isArray(keys) ? keys : [keys];
          let deleted = 0;
          for (const key of keyArray) {
            if (persistentStorage.has(key)) {
              persistentStorage.delete(key);
              deleted++;
            }
          }
          return deleted;
        }),
        exists: jest.fn(async (key: string) => {
          const entry = persistentStorage.get(key);
          if (!entry) return 0;
          if (entry.expireAt && Date.now() > entry.expireAt) {
            persistentStorage.delete(key);
            return 0;
          }
          return 1;
        }),
        scan: jest.fn(async (_cursor: number, options?: { MATCH?: string; COUNT?: number }) => {
          const pattern = options?.MATCH || '*';
          const regex = new RegExp(
            '^' + pattern.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*').replace(/\?/g, '.') + '$'
          );

          const matchingKeys: string[] = [];
          for (const key of persistentStorage.keys()) {
            if (regex.test(key)) {
              const entry = persistentStorage.get(key);
              if (entry && (!entry.expireAt || Date.now() <= entry.expireAt)) {
                matchingKeys.push(key);
              }
            }
          }

          return { cursor: 0, keys: matchingKeys };
        }),
        // Expose storage for test cleanup
        __storage__: persistentStorage,
      };
    };

    return {
      createClient: jest.fn(() => createMockClient()),
      __getStorage__: () => persistentStorage,
    };
  });
}

describe('E2E: MemoryService Data Persistence', () => {
  const TEST_PREFIX = 'e2e-test:';
  const REDIS_URL = process.env.REDIS_URL || 'redis://localhost:6379';

  // Get reference to shared storage for cleanup
  let sharedStorage: Map<string, any> | null = null;

  beforeAll(() => {
    if (!USE_REAL_REDIS) {
      // Get the shared storage from the mock
      const redis = require('redis');
      sharedStorage = redis.__getStorage__();
    }
  });

  beforeEach(() => {
    resetMemoryService();
  });

  afterEach(async () => {
    resetMemoryService();

    // Clean up test keys from storage
    if (sharedStorage) {
      for (const key of Array.from(sharedStorage.keys())) {
        if (key.startsWith(TEST_PREFIX)) {
          sharedStorage.delete(key);
        }
      }
    }
  });

  afterAll(async () => {
    // Final cleanup
    if (sharedStorage) {
      sharedStorage.clear();
    }
  });

  describe('Core Persistence Verification', () => {
    /**
     * E2E Test: Write data, restart service, verify data persists
     *
     * This is the core test for subtask-6-1:
     * 1. Start Redis container (simulated via persistent mock or real Redis)
     * 2. Start claude-flow service (MemoryService.initialize())
     * 3. Write test data via MemoryService
     * 4. Stop claude-flow service (MemoryService.disconnect())
     * 5. Restart claude-flow service (new MemoryService instance, initialize())
     * 6. Verify test data is retrievable
     */
    it('should persist data across service restart', async () => {
      // Phase 1: Initial service startup
      const service1 = new MemoryService({
        url: REDIS_URL,
        keyPrefix: TEST_PREFIX,
      });

      await service1.initialize();
      expect(service1.isConnected()).toBe(true);

      // Phase 2: Write test data
      const testData = {
        governanceDecision: {
          id: 'decision-123',
          timestamp: new Date().toISOString(),
          outcome: 'approved',
          confidence: 0.95,
          metadata: {
            policyId: 'policy-456',
            context: 'test-context',
          },
        },
      };

      const setResult = await service1.set('governance:decision:123', testData, { ttlSeconds: 0 });
      expect(setResult.success).toBe(true);

      // Verify data was written
      const immediateRead = await service1.get<typeof testData>('governance:decision:123');
      expect(immediateRead.found).toBe(true);
      expect(immediateRead.value).toEqual(testData);

      // Phase 3: Stop service (simulate service shutdown)
      await service1.disconnect();
      expect(service1.isConnected()).toBe(false);

      // Phase 4: Restart service (new instance simulates pod rescheduling)
      const service2 = new MemoryService({
        url: REDIS_URL,
        keyPrefix: TEST_PREFIX,
      });

      await service2.initialize();
      expect(service2.isConnected()).toBe(true);

      // Phase 5: Verify test data is retrievable
      const persistedData = await service2.get<typeof testData>('governance:decision:123');
      expect(persistedData.found).toBe(true);
      expect(persistedData.value).toEqual(testData);
      expect(persistedData.value?.governanceDecision.id).toBe('decision-123');
      expect(persistedData.value?.governanceDecision.outcome).toBe('approved');

      // Cleanup
      await service2.disconnect();
    });

    it('should persist multiple governance states across restart', async () => {
      // Phase 1: Start service and write multiple keys
      const service1 = new MemoryService({
        url: REDIS_URL,
        keyPrefix: TEST_PREFIX,
      });

      await service1.initialize();

      // Write various governance state types
      await service1.set('session:active:user-1', { userId: 'user-1', startTime: Date.now() }, { ttlSeconds: 0 });
      await service1.set('session:active:user-2', { userId: 'user-2', startTime: Date.now() }, { ttlSeconds: 0 });
      await service1.set('policy:cache:policy-1', { policyId: 'policy-1', rules: ['rule-a', 'rule-b'] }, { ttlSeconds: 0 });
      await service1.set('decision:history:001', { decisionId: '001', result: 'pass' }, { ttlSeconds: 0 });
      await service1.set('decision:history:002', { decisionId: '002', result: 'fail' }, { ttlSeconds: 0 });

      // Stop service
      await service1.disconnect();

      // Phase 2: Restart and verify all data persists
      const service2 = new MemoryService({
        url: REDIS_URL,
        keyPrefix: TEST_PREFIX,
      });

      await service2.initialize();

      // Verify all keys are retrievable
      const session1 = await service2.get<{ userId: string }>('session:active:user-1');
      const session2 = await service2.get<{ userId: string }>('session:active:user-2');
      const policy = await service2.get<{ policyId: string; rules: string[] }>('policy:cache:policy-1');
      const decision1 = await service2.get<{ decisionId: string; result: string }>('decision:history:001');
      const decision2 = await service2.get<{ decisionId: string; result: string }>('decision:history:002');

      expect(session1.found).toBe(true);
      expect(session1.value?.userId).toBe('user-1');

      expect(session2.found).toBe(true);
      expect(session2.value?.userId).toBe('user-2');

      expect(policy.found).toBe(true);
      expect(policy.value?.rules).toEqual(['rule-a', 'rule-b']);

      expect(decision1.found).toBe(true);
      expect(decision1.value?.result).toBe('pass');

      expect(decision2.found).toBe(true);
      expect(decision2.value?.result).toBe('fail');

      await service2.disconnect();
    });

    it('should handle graceful shutdown and preserve pending writes', async () => {
      const service = new MemoryService({
        url: REDIS_URL,
        keyPrefix: TEST_PREFIX,
      });

      await service.initialize();

      // Write data
      await service.set('pre-shutdown-key', { status: 'saved-before-shutdown' }, { ttlSeconds: 0 });

      // Graceful shutdown (await client.quit())
      await service.disconnect();

      // Verify no data loss after restart
      const service2 = new MemoryService({
        url: REDIS_URL,
        keyPrefix: TEST_PREFIX,
      });

      await service2.initialize();

      const result = await service2.get<{ status: string }>('pre-shutdown-key');
      expect(result.found).toBe(true);
      expect(result.value?.status).toBe('saved-before-shutdown');

      await service2.disconnect();
    });
  });

  describe('TTL Behavior Across Restarts', () => {
    it('should respect TTL expiration across service restarts', async () => {
      const service1 = new MemoryService({
        url: REDIS_URL,
        keyPrefix: TEST_PREFIX,
      });

      await service1.initialize();

      // Set key with very short TTL
      await service1.set('short-lived-key', 'temporary', { ttlSeconds: 1 });
      // Set key with no TTL (permanent)
      await service1.set('permanent-key', 'forever', { ttlSeconds: 0 });

      // Disconnect
      await service1.disconnect();

      // Wait for TTL to expire
      await new Promise((resolve) => setTimeout(resolve, 1100));

      // Restart
      const service2 = new MemoryService({
        url: REDIS_URL,
        keyPrefix: TEST_PREFIX,
      });

      await service2.initialize();

      // Short-lived key should be expired
      const shortLived = await service2.get<string>('short-lived-key');
      expect(shortLived.found).toBe(false);

      // Permanent key should still exist
      const permanent = await service2.get<string>('permanent-key');
      expect(permanent.found).toBe(true);
      expect(permanent.value).toBe('forever');

      await service2.disconnect();
    });
  });

  describe('Multiple Restart Cycles', () => {
    it('should maintain data integrity through multiple restart cycles', async () => {
      const cycleData = { cycle: 0, data: 'initial' };

      // Cycle 1: Write initial data
      const service1 = new MemoryService({
        url: REDIS_URL,
        keyPrefix: TEST_PREFIX,
      });
      await service1.initialize();
      await service1.set('cycle-data', cycleData, { ttlSeconds: 0 });
      await service1.disconnect();

      // Cycle 2: Read and update
      const service2 = new MemoryService({
        url: REDIS_URL,
        keyPrefix: TEST_PREFIX,
      });
      await service2.initialize();

      const read2 = await service2.get<typeof cycleData>('cycle-data');
      expect(read2.found).toBe(true);

      await service2.set('cycle-data', { cycle: 1, data: 'updated-cycle-1' }, { ttlSeconds: 0 });
      await service2.disconnect();

      // Cycle 3: Read and update again
      const service3 = new MemoryService({
        url: REDIS_URL,
        keyPrefix: TEST_PREFIX,
      });
      await service3.initialize();

      const read3 = await service3.get<typeof cycleData>('cycle-data');
      expect(read3.found).toBe(true);
      expect(read3.value?.cycle).toBe(1);
      expect(read3.value?.data).toBe('updated-cycle-1');

      await service3.set('cycle-data', { cycle: 2, data: 'final' }, { ttlSeconds: 0 });
      await service3.disconnect();

      // Cycle 4: Final verification
      const service4 = new MemoryService({
        url: REDIS_URL,
        keyPrefix: TEST_PREFIX,
      });
      await service4.initialize();

      const finalRead = await service4.get<typeof cycleData>('cycle-data');
      expect(finalRead.found).toBe(true);
      expect(finalRead.value?.cycle).toBe(2);
      expect(finalRead.value?.data).toBe('final');

      await service4.disconnect();
    });
  });

  describe('Complex Data Types Persistence', () => {
    it('should persist complex nested objects correctly', async () => {
      const complexData = {
        governanceContext: {
          sessionId: 'sess-123',
          userId: 'user-456',
          timestamp: '2024-01-15T10:30:00Z',
          decisions: [
            { id: 'd1', outcome: 'approved', confidence: 0.95 },
            { id: 'd2', outcome: 'denied', confidence: 0.88 },
          ],
          metadata: {
            source: 'api-gateway',
            version: '2.0.0',
            features: {
              adaptiveGovernance: true,
              mlEnabled: true,
            },
          },
          tags: ['production', 'high-priority'],
          numericValues: [1, 2.5, 3.14159],
        },
      };

      // Write complex data
      const service1 = new MemoryService({
        url: REDIS_URL,
        keyPrefix: TEST_PREFIX,
      });
      await service1.initialize();
      await service1.set('complex-governance-state', complexData, { ttlSeconds: 0 });
      await service1.disconnect();

      // Restart and verify
      const service2 = new MemoryService({
        url: REDIS_URL,
        keyPrefix: TEST_PREFIX,
      });
      await service2.initialize();

      const retrieved = await service2.get<typeof complexData>('complex-governance-state');
      expect(retrieved.found).toBe(true);
      expect(retrieved.value).toEqual(complexData);

      // Verify nested structure integrity
      expect(retrieved.value?.governanceContext.decisions).toHaveLength(2);
      expect(retrieved.value?.governanceContext.decisions[0].confidence).toBe(0.95);
      expect(retrieved.value?.governanceContext.metadata.features.mlEnabled).toBe(true);
      expect(retrieved.value?.governanceContext.tags).toContain('production');
      expect(retrieved.value?.governanceContext.numericValues[2]).toBeCloseTo(3.14159);

      await service2.disconnect();
    });

    it('should persist arrays and primitive values correctly', async () => {
      const service1 = new MemoryService({
        url: REDIS_URL,
        keyPrefix: TEST_PREFIX,
      });
      await service1.initialize();

      // Test various data types
      await service1.set('string-value', 'simple string', { ttlSeconds: 0 });
      await service1.set('number-value', 42, { ttlSeconds: 0 });
      await service1.set('boolean-value', true, { ttlSeconds: 0 });
      await service1.set('null-value', null, { ttlSeconds: 0 });
      await service1.set('array-value', [1, 'two', { three: 3 }], { ttlSeconds: 0 });

      await service1.disconnect();

      // Restart and verify
      const service2 = new MemoryService({
        url: REDIS_URL,
        keyPrefix: TEST_PREFIX,
      });
      await service2.initialize();

      expect((await service2.get<string>('string-value')).value).toBe('simple string');
      expect((await service2.get<number>('number-value')).value).toBe(42);
      expect((await service2.get<boolean>('boolean-value')).value).toBe(true);
      expect((await service2.get<null>('null-value')).value).toBe(null);

      const arrayResult = await service2.get<any[]>('array-value');
      expect(arrayResult.value).toEqual([1, 'two', { three: 3 }]);

      await service2.disconnect();
    });
  });

  describe('Cleanup Operations Across Restarts', () => {
    it('should allow cleanup of old data after restart', async () => {
      // Write data
      const service1 = new MemoryService({
        url: REDIS_URL,
        keyPrefix: '',  // No prefix for pattern matching
      });
      await service1.initialize();

      await service1.set('e2e-test:cleanup:key1', 'value1', { ttlSeconds: 0 });
      await service1.set('e2e-test:cleanup:key2', 'value2', { ttlSeconds: 0 });
      await service1.set('e2e-test:other:key3', 'value3', { ttlSeconds: 0 });

      await service1.disconnect();

      // Restart and cleanup
      const service2 = new MemoryService({
        url: REDIS_URL,
        keyPrefix: '',
      });
      await service2.initialize();

      // Cleanup only cleanup: keys
      const cleanupResult = await service2.cleanup('e2e-test:cleanup:*');
      expect(cleanupResult.success).toBe(true);
      expect(cleanupResult.deletedCount).toBe(2);

      // Verify cleanup was selective
      expect((await service2.get('e2e-test:cleanup:key1')).found).toBe(false);
      expect((await service2.get('e2e-test:cleanup:key2')).found).toBe(false);
      expect((await service2.get('e2e-test:other:key3')).found).toBe(true);

      // Cleanup remaining
      await service2.cleanup('e2e-test:*');
      await service2.disconnect();
    });
  });

  describe('Health Check After Restart', () => {
    it('should report healthy status after restart', async () => {
      const service1 = new MemoryService({
        url: REDIS_URL,
        keyPrefix: TEST_PREFIX,
      });
      await service1.initialize();

      const health1 = await service1.getHealth();
      expect(health1.healthy).toBe(true);
      expect(health1.connectionState).toBe('connected');

      await service1.disconnect();

      // Restart
      const service2 = new MemoryService({
        url: REDIS_URL,
        keyPrefix: TEST_PREFIX,
      });
      await service2.initialize();

      const health2 = await service2.getHealth();
      expect(health2.healthy).toBe(true);
      expect(health2.connectionState).toBe('connected');
      expect(health2.latencyMs).toBeDefined();
      expect(health2.latencyMs).toBeGreaterThanOrEqual(0);

      await service2.disconnect();
    });
  });
});

/**
 * Manual E2E Verification Instructions
 *
 * To verify persistence with a real Redis instance:
 *
 * 1. Start Redis:
 *    docker run -d --name redis-e2e -p 6379:6379 redis:7-alpine redis-server --appendonly yes
 *
 * 2. Run E2E tests with real Redis:
 *    cd claude-flow
 *    RUN_REAL_REDIS_TESTS=true REDIS_URL=redis://localhost:6379 npm test -- memory.e2e.test.ts
 *
 * 3. Manual verification (optional):
 *    - Write data using the test
 *    - Stop Redis: docker stop redis-e2e
 *    - Start Redis: docker start redis-e2e
 *    - Verify data by running tests again or using redis-cli:
 *      docker exec -it redis-e2e redis-cli KEYS '*'
 *
 * 4. Cleanup:
 *    docker stop redis-e2e && docker rm redis-e2e
 */
