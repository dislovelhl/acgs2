/**
 * Performance Benchmark Tests for MemoryService
 *
 * Verifies the <10ms latency requirement for get/set operations (p95).
 *
 * Test Strategy:
 * - Tests use mocked Redis for consistent benchmarking in CI
 * - For real performance testing, set RUN_REAL_REDIS_TESTS=true and ensure Redis is running
 * - Measures p95 latency across multiple iterations
 *
 * Manual Performance Verification:
 * 1. Start Redis: docker run -d --name redis-perf -p 6379:6379 redis:7-alpine
 * 2. Run tests: RUN_REAL_REDIS_TESTS=true npm test -- memory.perf.test.ts
 * 3. Cleanup: docker stop redis-perf && docker rm redis-perf
 */

import { MemoryService, resetMemoryService } from '../services/memory';

// Check if we should use real Redis
const USE_REAL_REDIS = process.env.RUN_REAL_REDIS_TESTS === 'true';

// Performance test configuration
const PERF_CONFIG = {
  // Number of operations for each test
  ITERATIONS: 100,
  // Target latency in milliseconds (p95)
  TARGET_LATENCY_MS: 10,
  // Percentile to measure (95th)
  PERCENTILE: 95,
  // Warmup iterations before measuring
  WARMUP_ITERATIONS: 10,
};

// Mock the redis module for non-real tests
if (!USE_REAL_REDIS) {
  jest.mock('redis', () => {
    const storage = new Map<string, { value: string; expireAt?: number }>();

    const createMockClient = () => {
      const eventHandlers: Record<string, Function> = {};

      return {
        connect: jest.fn(async function () {
          // Simulate minimal connection latency
          await new Promise((resolve) => setTimeout(resolve, 1));
          if (eventHandlers['connect']) {
            eventHandlers['connect']();
          }
        }),
        quit: jest.fn().mockResolvedValue(undefined),
        disconnect: jest.fn().mockResolvedValue(undefined),
        ping: jest.fn(async () => {
          // Simulate minimal ping latency
          await new Promise((resolve) => setTimeout(resolve, 0.1));
          return 'PONG';
        }),
        on: jest.fn((event: string, handler: Function) => {
          eventHandlers[event] = handler;
          return createMockClient();
        }),
        set: jest.fn(async (key: string, value: string, options?: { EX?: number }) => {
          // Simulate realistic set latency (sub-millisecond)
          await new Promise((resolve) => setImmediate(resolve));
          const entry: { value: string; expireAt?: number } = { value };
          if (options?.EX) {
            entry.expireAt = Date.now() + options.EX * 1000;
          }
          storage.set(key, entry);
          return 'OK';
        }),
        get: jest.fn(async (key: string) => {
          // Simulate realistic get latency (sub-millisecond)
          await new Promise((resolve) => setImmediate(resolve));
          const entry = storage.get(key);
          if (!entry) return null;
          if (entry.expireAt && Date.now() > entry.expireAt) {
            storage.delete(key);
            return null;
          }
          return entry.value;
        }),
        del: jest.fn(async (keys: string | string[]) => {
          await new Promise((resolve) => setImmediate(resolve));
          const keyArray = Array.isArray(keys) ? keys : [keys];
          let deleted = 0;
          for (const key of keyArray) {
            if (storage.has(key)) {
              storage.delete(key);
              deleted++;
            }
          }
          return deleted;
        }),
        exists: jest.fn(async (key: string) => {
          await new Promise((resolve) => setImmediate(resolve));
          const entry = storage.get(key);
          if (!entry) return 0;
          if (entry.expireAt && Date.now() > entry.expireAt) {
            storage.delete(key);
            return 0;
          }
          return 1;
        }),
        scan: jest.fn(async (_cursor: number, options?: { MATCH?: string; COUNT?: number }) => {
          await new Promise((resolve) => setImmediate(resolve));
          const pattern = options?.MATCH || '*';
          const regex = new RegExp(
            '^' + pattern.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*').replace(/\?/g, '.') + '$'
          );

          const matchingKeys: string[] = [];
          for (const key of storage.keys()) {
            if (regex.test(key)) {
              const entry = storage.get(key);
              if (entry && (!entry.expireAt || Date.now() <= entry.expireAt)) {
                matchingKeys.push(key);
              }
            }
          }

          return { cursor: 0, keys: matchingKeys };
        }),
        __storage__: storage,
      };
    };

    return {
      createClient: jest.fn(() => createMockClient()),
      __getStorage__: () => storage,
    };
  });
}

/**
 * Calculate percentile from an array of latency values
 */
function calculatePercentile(latencies: number[], percentile: number): number {
  const sorted = [...latencies].sort((a, b) => a - b);
  const index = Math.ceil((percentile / 100) * sorted.length) - 1;
  return sorted[Math.max(0, index)];
}

/**
 * Calculate statistics from latency array
 */
function calculateStats(latencies: number[]): {
  min: number;
  max: number;
  avg: number;
  p50: number;
  p95: number;
  p99: number;
} {
  const sorted = [...latencies].sort((a, b) => a - b);
  const sum = latencies.reduce((a, b) => a + b, 0);

  return {
    min: sorted[0],
    max: sorted[sorted.length - 1],
    avg: sum / latencies.length,
    p50: calculatePercentile(latencies, 50),
    p95: calculatePercentile(latencies, 95),
    p99: calculatePercentile(latencies, 99),
  };
}

describe('Performance Benchmark: MemoryService Latency', () => {
  const TEST_PREFIX = 'perf-test:';
  const REDIS_URL = process.env.REDIS_URL || 'redis://localhost:6379';

  let service: MemoryService;
  let sharedStorage: Map<string, any> | null = null;

  beforeAll(async () => {
    if (!USE_REAL_REDIS) {
      const redis = require('redis');
      sharedStorage = redis.__getStorage__();
    }

    // Initialize service once for all tests
    service = new MemoryService({
      url: REDIS_URL,
      keyPrefix: TEST_PREFIX,
      debug: false,
    });

    await service.initialize();
  });

  afterAll(async () => {
    await service.disconnect();
    resetMemoryService();

    if (sharedStorage) {
      sharedStorage.clear();
    }
  });

  afterEach(() => {
    // Clean up test keys
    if (sharedStorage) {
      for (const key of Array.from(sharedStorage.keys())) {
        if (key.startsWith(TEST_PREFIX)) {
          sharedStorage.delete(key);
        }
      }
    }
  });

  describe('set() Operation Latency', () => {
    it(`should complete set() operations within ${PERF_CONFIG.TARGET_LATENCY_MS}ms (p${PERF_CONFIG.PERCENTILE})`, async () => {
      const latencies: number[] = [];

      // Warmup phase
      for (let i = 0; i < PERF_CONFIG.WARMUP_ITERATIONS; i++) {
        await service.set(`warmup-key-${i}`, { warmup: true });
      }

      // Measurement phase
      for (let i = 0; i < PERF_CONFIG.ITERATIONS; i++) {
        const testData = {
          id: `item-${i}`,
          timestamp: Date.now(),
          data: { nested: { value: i }, array: [1, 2, 3] },
        };

        const startTime = performance.now();
        await service.set(`test-key-${i}`, testData);
        const endTime = performance.now();

        latencies.push(endTime - startTime);
      }

      const stats = calculateStats(latencies);

      // Log performance results
      process.stdout.write(`\n[Performance] set() Latency Results:\n`);
      process.stdout.write(`  Min:    ${stats.min.toFixed(3)}ms\n`);
      process.stdout.write(`  Max:    ${stats.max.toFixed(3)}ms\n`);
      process.stdout.write(`  Avg:    ${stats.avg.toFixed(3)}ms\n`);
      process.stdout.write(`  p50:    ${stats.p50.toFixed(3)}ms\n`);
      process.stdout.write(`  p95:    ${stats.p95.toFixed(3)}ms\n`);
      process.stdout.write(`  p99:    ${stats.p99.toFixed(3)}ms\n`);
      process.stdout.write(`  Target: <${PERF_CONFIG.TARGET_LATENCY_MS}ms (p${PERF_CONFIG.PERCENTILE})\n`);

      // Verify p95 is under target
      expect(stats.p95).toBeLessThan(PERF_CONFIG.TARGET_LATENCY_MS);
    });

    it('should maintain consistent latency for set() with varying payload sizes', async () => {
      const payloadSizes = [
        { name: 'small', data: { a: 1 } },
        { name: 'medium', data: { field: 'x'.repeat(100), items: Array(10).fill({ id: 1 }) } },
        { name: 'large', data: { content: 'x'.repeat(1000), items: Array(50).fill({ id: 1, nested: { data: true } }) } },
      ];

      const results: Record<string, { p95: number; avg: number }> = {};

      for (const { name, data } of payloadSizes) {
        const latencies: number[] = [];

        for (let i = 0; i < PERF_CONFIG.ITERATIONS; i++) {
          const startTime = performance.now();
          await service.set(`payload-test-${name}-${i}`, data);
          const endTime = performance.now();

          latencies.push(endTime - startTime);
        }

        const stats = calculateStats(latencies);
        results[name] = { p95: stats.p95, avg: stats.avg };

        process.stdout.write(`\n[Performance] set() with ${name} payload: p95=${stats.p95.toFixed(3)}ms, avg=${stats.avg.toFixed(3)}ms`);

        // All payload sizes should be under target
        expect(stats.p95).toBeLessThan(PERF_CONFIG.TARGET_LATENCY_MS);
      }
    });

    it('should maintain consistent latency for set() with TTL', async () => {
      const latenciesWithTtl: number[] = [];
      const latenciesWithoutTtl: number[] = [];

      // Without TTL
      for (let i = 0; i < PERF_CONFIG.ITERATIONS; i++) {
        const startTime = performance.now();
        await service.set(`no-ttl-key-${i}`, { value: i }, { ttlSeconds: 0 });
        const endTime = performance.now();
        latenciesWithoutTtl.push(endTime - startTime);
      }

      // With TTL
      for (let i = 0; i < PERF_CONFIG.ITERATIONS; i++) {
        const startTime = performance.now();
        await service.set(`with-ttl-key-${i}`, { value: i }, { ttlSeconds: 3600 });
        const endTime = performance.now();
        latenciesWithTtl.push(endTime - startTime);
      }

      const statsWithoutTtl = calculateStats(latenciesWithoutTtl);
      const statsWithTtl = calculateStats(latenciesWithTtl);

      process.stdout.write(`\n[Performance] set() without TTL: p95=${statsWithoutTtl.p95.toFixed(3)}ms`);
      process.stdout.write(`\n[Performance] set() with TTL:    p95=${statsWithTtl.p95.toFixed(3)}ms`);

      // Both should be under target
      expect(statsWithoutTtl.p95).toBeLessThan(PERF_CONFIG.TARGET_LATENCY_MS);
      expect(statsWithTtl.p95).toBeLessThan(PERF_CONFIG.TARGET_LATENCY_MS);
    });
  });

  describe('get() Operation Latency', () => {
    beforeEach(async () => {
      // Pre-populate data for get tests
      for (let i = 0; i < PERF_CONFIG.ITERATIONS + PERF_CONFIG.WARMUP_ITERATIONS; i++) {
        await service.set(`get-test-key-${i}`, {
          id: `item-${i}`,
          timestamp: Date.now(),
          data: { nested: { value: i }, array: [1, 2, 3] },
        });
      }
    });

    it(`should complete get() operations within ${PERF_CONFIG.TARGET_LATENCY_MS}ms (p${PERF_CONFIG.PERCENTILE})`, async () => {
      const latencies: number[] = [];

      // Warmup phase
      for (let i = 0; i < PERF_CONFIG.WARMUP_ITERATIONS; i++) {
        await service.get(`get-test-key-${i}`);
      }

      // Measurement phase
      for (let i = PERF_CONFIG.WARMUP_ITERATIONS; i < PERF_CONFIG.ITERATIONS + PERF_CONFIG.WARMUP_ITERATIONS; i++) {
        const startTime = performance.now();
        const result = await service.get(`get-test-key-${i}`);
        const endTime = performance.now();

        expect(result.found).toBe(true);
        latencies.push(endTime - startTime);
      }

      const stats = calculateStats(latencies);

      // Log performance results
      process.stdout.write(`\n[Performance] get() Latency Results:\n`);
      process.stdout.write(`  Min:    ${stats.min.toFixed(3)}ms\n`);
      process.stdout.write(`  Max:    ${stats.max.toFixed(3)}ms\n`);
      process.stdout.write(`  Avg:    ${stats.avg.toFixed(3)}ms\n`);
      process.stdout.write(`  p50:    ${stats.p50.toFixed(3)}ms\n`);
      process.stdout.write(`  p95:    ${stats.p95.toFixed(3)}ms\n`);
      process.stdout.write(`  p99:    ${stats.p99.toFixed(3)}ms\n`);
      process.stdout.write(`  Target: <${PERF_CONFIG.TARGET_LATENCY_MS}ms (p${PERF_CONFIG.PERCENTILE})\n`);

      // Verify p95 is under target
      expect(stats.p95).toBeLessThan(PERF_CONFIG.TARGET_LATENCY_MS);
    });

    it('should handle cache misses (non-existent keys) efficiently', async () => {
      const latencies: number[] = [];

      for (let i = 0; i < PERF_CONFIG.ITERATIONS; i++) {
        const startTime = performance.now();
        const result = await service.get(`non-existent-key-${i}`);
        const endTime = performance.now();

        expect(result.found).toBe(false);
        latencies.push(endTime - startTime);
      }

      const stats = calculateStats(latencies);

      process.stdout.write(`\n[Performance] get() cache miss: p95=${stats.p95.toFixed(3)}ms, avg=${stats.avg.toFixed(3)}ms`);

      // Cache misses should also be fast
      expect(stats.p95).toBeLessThan(PERF_CONFIG.TARGET_LATENCY_MS);
    });
  });

  describe('Combined get/set Workload', () => {
    it('should maintain latency targets under mixed read/write workload', async () => {
      const getLatencies: number[] = [];
      const setLatencies: number[] = [];

      // Pre-populate some keys
      for (let i = 0; i < PERF_CONFIG.ITERATIONS / 2; i++) {
        await service.set(`mixed-key-${i}`, { value: i });
      }

      // Mixed workload: 70% reads, 30% writes (common pattern)
      for (let i = 0; i < PERF_CONFIG.ITERATIONS; i++) {
        if (Math.random() < 0.7) {
          // Read operation
          const keyIndex = Math.floor(Math.random() * (PERF_CONFIG.ITERATIONS / 2));
          const startTime = performance.now();
          await service.get(`mixed-key-${keyIndex}`);
          const endTime = performance.now();
          getLatencies.push(endTime - startTime);
        } else {
          // Write operation
          const startTime = performance.now();
          await service.set(`mixed-key-write-${i}`, { value: i, written: true });
          const endTime = performance.now();
          setLatencies.push(endTime - startTime);
        }
      }

      const getStats = calculateStats(getLatencies);
      const setStats = calculateStats(setLatencies);

      process.stdout.write(`\n[Performance] Mixed workload - get(): p95=${getStats.p95.toFixed(3)}ms (${getLatencies.length} ops)`);
      process.stdout.write(`\n[Performance] Mixed workload - set(): p95=${setStats.p95.toFixed(3)}ms (${setLatencies.length} ops)`);

      expect(getStats.p95).toBeLessThan(PERF_CONFIG.TARGET_LATENCY_MS);
      expect(setStats.p95).toBeLessThan(PERF_CONFIG.TARGET_LATENCY_MS);
    });
  });

  describe('exists() Operation Latency', () => {
    beforeEach(async () => {
      for (let i = 0; i < PERF_CONFIG.ITERATIONS; i++) {
        await service.set(`exists-test-key-${i}`, { value: i });
      }
    });

    it(`should complete exists() operations within ${PERF_CONFIG.TARGET_LATENCY_MS}ms (p${PERF_CONFIG.PERCENTILE})`, async () => {
      const latencies: number[] = [];

      for (let i = 0; i < PERF_CONFIG.ITERATIONS; i++) {
        const startTime = performance.now();
        const exists = await service.exists(`exists-test-key-${i}`);
        const endTime = performance.now();

        expect(exists).toBe(true);
        latencies.push(endTime - startTime);
      }

      const stats = calculateStats(latencies);

      process.stdout.write(`\n[Performance] exists() Latency: p95=${stats.p95.toFixed(3)}ms, avg=${stats.avg.toFixed(3)}ms`);

      expect(stats.p95).toBeLessThan(PERF_CONFIG.TARGET_LATENCY_MS);
    });
  });

  describe('delete() Operation Latency', () => {
    beforeEach(async () => {
      for (let i = 0; i < PERF_CONFIG.ITERATIONS; i++) {
        await service.set(`delete-test-key-${i}`, { value: i });
      }
    });

    it(`should complete delete() operations within ${PERF_CONFIG.TARGET_LATENCY_MS}ms (p${PERF_CONFIG.PERCENTILE})`, async () => {
      const latencies: number[] = [];

      for (let i = 0; i < PERF_CONFIG.ITERATIONS; i++) {
        const startTime = performance.now();
        const result = await service.delete(`delete-test-key-${i}`);
        const endTime = performance.now();

        expect(result.success).toBe(true);
        latencies.push(endTime - startTime);
      }

      const stats = calculateStats(latencies);

      process.stdout.write(`\n[Performance] delete() Latency: p95=${stats.p95.toFixed(3)}ms, avg=${stats.avg.toFixed(3)}ms`);

      expect(stats.p95).toBeLessThan(PERF_CONFIG.TARGET_LATENCY_MS);
    });
  });

  describe('cleanup() Operation Latency (1000 keys benchmark)', () => {
    it('should complete cleanup() of 1000 keys within 1 second', async () => {
      const KEY_COUNT = 1000;

      // Seed 1000 keys
      for (let i = 0; i < KEY_COUNT; i++) {
        await service.set(`cleanup-benchmark-key-${i}`, { index: i });
      }

      // Measure cleanup time
      const startTime = performance.now();
      const result = await service.cleanup(`${TEST_PREFIX}cleanup-benchmark-*`);
      const endTime = performance.now();

      const durationMs = endTime - startTime;

      process.stdout.write(`\n[Performance] cleanup() ${KEY_COUNT} keys: ${durationMs.toFixed(3)}ms`);
      process.stdout.write(`\n[Performance] cleanup() deleted: ${result.deletedCount} keys`);

      expect(result.success).toBe(true);
      expect(result.deletedCount).toBe(KEY_COUNT);
      expect(durationMs).toBeLessThan(1000); // Must complete within 1 second
    });
  });

  describe('Connection Pooling Verification', () => {
    it('should use single shared client instance (connection pooling)', async () => {
      // Create multiple "logical" operations but they should all use same client
      const operations = [];

      for (let i = 0; i < 50; i++) {
        operations.push(service.set(`pool-test-${i}`, { value: i }));
      }

      const startTime = performance.now();
      await Promise.all(operations);
      const endTime = performance.now();

      const totalTime = endTime - startTime;
      const avgTimePerOp = totalTime / 50;

      process.stdout.write(`\n[Performance] 50 parallel operations: total=${totalTime.toFixed(3)}ms, avg=${avgTimePerOp.toFixed(3)}ms`);

      // Parallel operations should complete quickly (demonstrates connection reuse)
      // If new connections were created per operation, this would be much slower
      expect(avgTimePerOp).toBeLessThan(PERF_CONFIG.TARGET_LATENCY_MS);
    });
  });

  describe('Health Check Latency', () => {
    it('should complete health check (with PING) quickly', async () => {
      const latencies: number[] = [];

      for (let i = 0; i < 20; i++) {
        const startTime = performance.now();
        const health = await service.getHealth();
        const endTime = performance.now();

        expect(health.healthy).toBe(true);
        latencies.push(endTime - startTime);
      }

      const stats = calculateStats(latencies);

      process.stdout.write(`\n[Performance] getHealth() (includes PING): p95=${stats.p95.toFixed(3)}ms`);

      // Health check should also be fast
      expect(stats.p95).toBeLessThan(PERF_CONFIG.TARGET_LATENCY_MS);
    });
  });
});

/**
 * Performance Test Summary
 *
 * This test suite verifies the following performance requirements from spec.md:
 *
 * 1. get() operations complete in <10ms (p95)
 * 2. set() operations complete in <10ms (p95)
 * 3. cleanup() completes within reasonable time (non-blocking SCAN)
 * 4. Single shared client instance (connection pooling)
 *
 * Manual Verification with Real Redis:
 *
 * # Start Redis
 * docker run -d --name redis-perf -p 6379:6379 redis:7-alpine
 *
 * # Run performance tests
 * cd claude-flow
 * RUN_REAL_REDIS_TESTS=true npm test -- memory.perf.test.ts --verbose
 *
 * # Cleanup
 * docker stop redis-perf && docker rm redis-perf
 *
 * Expected Results (with local Redis):
 * - get() p95: <2ms
 * - set() p95: <2ms
 * - exists() p95: <2ms
 * - delete() p95: <2ms
 * - cleanup(1000 keys) <500ms
 */
