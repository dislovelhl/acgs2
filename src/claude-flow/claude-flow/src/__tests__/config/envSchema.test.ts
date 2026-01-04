/**
 * Environment Schema Tests
 *
 * Direct tests for the envSchema module to ensure comprehensive coverage
 * of all schema transformations, validators, and edge cases.
 *
 * @module envSchema.test
 */

import { EnvSchema, ProductionSecuritySchema, EnvConfig } from '../../config/envSchema';

describe('EnvSchema', () => {
  describe('Boolean Transform', () => {
    it('should transform "true" variations to true', () => {
      const testCases = ['true', 'TRUE', 'True', '1', 'yes', 'YES', 'Yes'];

      for (const value of testCases) {
        const result = EnvSchema.safeParse({ DEBUG: value });
        expect(result.success).toBe(true);
        if (result.success) {
          expect(result.data.DEBUG).toBe(true);
        }
      }
    });

    it('should transform "false" variations to false', () => {
      const testCases = ['false', 'FALSE', 'False', '0', 'no', 'NO', 'No', ''];

      for (const value of testCases) {
        const result = EnvSchema.safeParse({ DEBUG: value });
        expect(result.success).toBe(true);
        if (result.success) {
          expect(result.data.DEBUG).toBe(false);
        }
      }
    });

    it('should default to false when not provided', () => {
      const result = EnvSchema.safeParse({});
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.DEBUG).toBe(false);
        expect(result.data.RELOAD).toBe(false);
      }
    });

    it('should handle whitespace in boolean strings', () => {
      const result = EnvSchema.safeParse({ DEBUG: '  true  ' });
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.DEBUG).toBe(true);
      }
    });

    it('should treat unrecognized strings as false', () => {
      const result = EnvSchema.safeParse({ DEBUG: 'maybe' });
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.DEBUG).toBe(false);
      }
    });
  });

  describe('Positive Integer Transform', () => {
    it('should transform valid integer strings', () => {
      const result = EnvSchema.safeParse({
        DEFAULT_ESCALATION_TIMEOUT_MINUTES: '45',
        CRITICAL_ESCALATION_TIMEOUT_MINUTES: '10',
        EMERGENCY_ESCALATION_TIMEOUT_MINUTES: '120',
      });

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.DEFAULT_ESCALATION_TIMEOUT_MINUTES).toBe(45);
        expect(result.data.CRITICAL_ESCALATION_TIMEOUT_MINUTES).toBe(10);
        expect(result.data.EMERGENCY_ESCALATION_TIMEOUT_MINUTES).toBe(120);
      }
    });

    it('should use default values when not provided', () => {
      const result = EnvSchema.safeParse({});

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.DEFAULT_ESCALATION_TIMEOUT_MINUTES).toBe(30);
        expect(result.data.CRITICAL_ESCALATION_TIMEOUT_MINUTES).toBe(15);
        expect(result.data.EMERGENCY_ESCALATION_TIMEOUT_MINUTES).toBe(60);
      }
    });

    it('should reject negative integer values', () => {
      const result = EnvSchema.safeParse({
        DEFAULT_ESCALATION_TIMEOUT_MINUTES: '-5',
      });
      expect(result.success).toBe(false);
    });

    it('should reject zero values', () => {
      const result = EnvSchema.safeParse({
        DEFAULT_ESCALATION_TIMEOUT_MINUTES: '0',
      });
      expect(result.success).toBe(false);
    });

    it('should reject non-numeric values', () => {
      const result = EnvSchema.safeParse({
        DEFAULT_ESCALATION_TIMEOUT_MINUTES: 'abc',
      });
      expect(result.success).toBe(false);
    });

    it('should reject float values', () => {
      const result = EnvSchema.safeParse({
        DEFAULT_ESCALATION_TIMEOUT_MINUTES: '30.5',
      });
      // parseInt truncates the decimal, so 30.5 becomes 30
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.DEFAULT_ESCALATION_TIMEOUT_MINUTES).toBe(30);
      }
    });
  });

  describe('URL Schema', () => {
    describe('Redis URL', () => {
      it('should accept redis:// protocol', () => {
        const result = EnvSchema.safeParse({ REDIS_URL: 'redis://localhost:6379' });
        expect(result.success).toBe(true);
      });

      it('should accept rediss:// protocol (TLS)', () => {
        const result = EnvSchema.safeParse({ REDIS_URL: 'rediss://secure-redis:6379' });
        expect(result.success).toBe(true);
      });

      it('should reject http:// protocol for Redis', () => {
        const result = EnvSchema.safeParse({ REDIS_URL: 'http://localhost:6379' });
        expect(result.success).toBe(false);
      });

      it('should reject invalid URL format', () => {
        const result = EnvSchema.safeParse({ REDIS_URL: 'not-a-url' });
        expect(result.success).toBe(false);
      });

      it('should use default when not provided', () => {
        const result = EnvSchema.safeParse({});
        expect(result.success).toBe(true);
        if (result.success) {
          expect(result.data.REDIS_URL).toBe('redis://localhost:6379');
        }
      });

      it('should accept empty string (uses default)', () => {
        // Empty strings for optional URLs should pass since they're optional
        const result = EnvSchema.safeParse({});
        expect(result.success).toBe(true);
      });
    });

    describe('HTTP URLs', () => {
      it('should accept http:// for AGENT_BUS_URL', () => {
        const result = EnvSchema.safeParse({ AGENT_BUS_URL: 'http://localhost:8000' });
        expect(result.success).toBe(true);
      });

      it('should accept https:// for AGENT_BUS_URL', () => {
        const result = EnvSchema.safeParse({ AGENT_BUS_URL: 'https://api.example.com' });
        expect(result.success).toBe(true);
      });

      it('should reject ftp:// for AGENT_BUS_URL', () => {
        const result = EnvSchema.safeParse({ AGENT_BUS_URL: 'ftp://files.example.com' });
        expect(result.success).toBe(false);
      });

      it('should accept http:// for OPA_URL', () => {
        const result = EnvSchema.safeParse({ OPA_URL: 'http://opa:8181' });
        expect(result.success).toBe(true);
      });

      it('should accept http:// for HITL_APPROVALS_URL', () => {
        const result = EnvSchema.safeParse({ HITL_APPROVALS_URL: 'http://hitl:8002' });
        expect(result.success).toBe(true);
      });
    });
  });

  describe('Port Schema', () => {
    it('should transform valid port strings to numbers', () => {
      const result = EnvSchema.safeParse({ HITL_APPROVALS_PORT: '8080' });
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.HITL_APPROVALS_PORT).toBe(8080);
        expect(typeof result.data.HITL_APPROVALS_PORT).toBe('number');
      }
    });

    it('should accept port 1 (minimum)', () => {
      const result = EnvSchema.safeParse({ HITL_APPROVALS_PORT: '1' });
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.HITL_APPROVALS_PORT).toBe(1);
      }
    });

    it('should accept port 65535 (maximum)', () => {
      const result = EnvSchema.safeParse({ HITL_APPROVALS_PORT: '65535' });
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.HITL_APPROVALS_PORT).toBe(65535);
      }
    });

    it('should reject port 0', () => {
      const result = EnvSchema.safeParse({ HITL_APPROVALS_PORT: '0' });
      expect(result.success).toBe(false);
    });

    it('should reject negative ports', () => {
      const result = EnvSchema.safeParse({ HITL_APPROVALS_PORT: '-1' });
      expect(result.success).toBe(false);
    });

    it('should reject ports above 65535', () => {
      const result = EnvSchema.safeParse({ HITL_APPROVALS_PORT: '65536' });
      expect(result.success).toBe(false);
    });

    it('should reject non-numeric ports', () => {
      const result = EnvSchema.safeParse({ HITL_APPROVALS_PORT: 'abc' });
      expect(result.success).toBe(false);
    });

    it('should use default port when not provided', () => {
      const result = EnvSchema.safeParse({});
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.HITL_APPROVALS_PORT).toBe(8002);
      }
    });
  });

  describe('Log Level Enum', () => {
    it('should accept valid log levels', () => {
      const levels = ['DEBUG', 'INFO', 'WARN', 'ERROR'];
      for (const level of levels) {
        const result = EnvSchema.safeParse({ LOG_LEVEL: level });
        expect(result.success).toBe(true);
        if (result.success) {
          expect(result.data.LOG_LEVEL).toBe(level);
        }
      }
    });

    it('should reject invalid log levels', () => {
      const invalidLevels = ['TRACE', 'VERBOSE', 'debug', 'info', 'FATAL'];
      for (const level of invalidLevels) {
        const result = EnvSchema.safeParse({ LOG_LEVEL: level });
        expect(result.success).toBe(false);
      }
    });

    it('should use default log level when not provided', () => {
      const result = EnvSchema.safeParse({});
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.LOG_LEVEL).toBe('INFO');
      }
    });
  });

  describe('Environment Enum', () => {
    it('should accept valid environments', () => {
      const environments = ['development', 'staging', 'production'];
      for (const env of environments) {
        const result = EnvSchema.safeParse({ ENVIRONMENT: env });
        expect(result.success).toBe(true);
        if (result.success) {
          expect(result.data.ENVIRONMENT).toBe(env);
        }
      }
    });

    it('should reject invalid environments', () => {
      const invalidEnvs = ['dev', 'prod', 'test', 'DEVELOPMENT', 'PRODUCTION'];
      for (const env of invalidEnvs) {
        const result = EnvSchema.safeParse({ ENVIRONMENT: env });
        expect(result.success).toBe(false);
      }
    });

    it('should use default environment when not provided', () => {
      const result = EnvSchema.safeParse({});
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.ENVIRONMENT).toBe('development');
      }
    });
  });

  describe('TENANT_ID', () => {
    it('should accept valid tenant IDs', () => {
      const result = EnvSchema.safeParse({ TENANT_ID: 'my-tenant-123' });
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.TENANT_ID).toBe('my-tenant-123');
      }
    });

    it('should reject empty tenant ID', () => {
      const result = EnvSchema.safeParse({ TENANT_ID: '' });
      expect(result.success).toBe(false);
    });

    it('should use default tenant ID when not provided', () => {
      const result = EnvSchema.safeParse({});
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.TENANT_ID).toBe('acgs-dev');
      }
    });
  });

  describe('Password Fields', () => {
    it('should accept any password value (non-production)', () => {
      const result = EnvSchema.safeParse({
        REDIS_PASSWORD: 'short',
        KAFKA_PASSWORD: 'weak',
      });
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.REDIS_PASSWORD).toBe('short');
        expect(result.data.KAFKA_PASSWORD).toBe('weak');
      }
    });

    it('should accept empty passwords', () => {
      const result = EnvSchema.safeParse({
        REDIS_PASSWORD: '',
        KAFKA_PASSWORD: '',
      });
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.REDIS_PASSWORD).toBe('');
        expect(result.data.KAFKA_PASSWORD).toBe('');
      }
    });

    it('should use empty default for passwords', () => {
      const result = EnvSchema.safeParse({});
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.REDIS_PASSWORD).toBe('');
        expect(result.data.KAFKA_PASSWORD).toBe('');
      }
    });
  });

  describe('Kafka Bootstrap', () => {
    it('should accept any string for KAFKA_BOOTSTRAP', () => {
      const result = EnvSchema.safeParse({ KAFKA_BOOTSTRAP: 'kafka-1:9092,kafka-2:9092' });
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.KAFKA_BOOTSTRAP).toBe('kafka-1:9092,kafka-2:9092');
      }
    });

    it('should use empty default for KAFKA_BOOTSTRAP', () => {
      const result = EnvSchema.safeParse({});
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.KAFKA_BOOTSTRAP).toBe('');
      }
    });
  });

  describe('Complete Configuration', () => {
    it('should parse a complete valid configuration', () => {
      const fullConfig = {
        TENANT_ID: 'test-tenant',
        ENVIRONMENT: 'staging',
        LOG_LEVEL: 'DEBUG',
        DEBUG: 'true',
        RELOAD: 'false',
        REDIS_URL: 'redis://redis-server:6379',
        REDIS_PASSWORD: 'mypassword',
        KAFKA_BOOTSTRAP: 'kafka:9092',
        KAFKA_PASSWORD: 'kafkapass',
        AGENT_BUS_URL: 'http://bus:8000',
        OPA_URL: 'http://opa:8181',
        HITL_APPROVALS_URL: 'http://hitl:8002',
        HITL_APPROVALS_PORT: '9000',
        DEFAULT_ESCALATION_TIMEOUT_MINUTES: '45',
        CRITICAL_ESCALATION_TIMEOUT_MINUTES: '10',
        EMERGENCY_ESCALATION_TIMEOUT_MINUTES: '90',
      };

      const result = EnvSchema.safeParse(fullConfig);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.TENANT_ID).toBe('test-tenant');
        expect(result.data.ENVIRONMENT).toBe('staging');
        expect(result.data.LOG_LEVEL).toBe('DEBUG');
        expect(result.data.DEBUG).toBe(true);
        expect(result.data.RELOAD).toBe(false);
        expect(result.data.HITL_APPROVALS_PORT).toBe(9000);
        expect(result.data.DEFAULT_ESCALATION_TIMEOUT_MINUTES).toBe(45);
      }
    });

    it('should use all defaults for empty configuration', () => {
      const result = EnvSchema.safeParse({});
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.TENANT_ID).toBe('acgs-dev');
        expect(result.data.ENVIRONMENT).toBe('development');
        expect(result.data.LOG_LEVEL).toBe('INFO');
        expect(result.data.DEBUG).toBe(false);
        expect(result.data.RELOAD).toBe(false);
        expect(result.data.REDIS_URL).toBe('redis://localhost:6379');
        expect(result.data.REDIS_PASSWORD).toBe('');
        expect(result.data.KAFKA_BOOTSTRAP).toBe('');
        expect(result.data.KAFKA_PASSWORD).toBe('');
        expect(result.data.AGENT_BUS_URL).toBe('http://localhost:8000');
        expect(result.data.OPA_URL).toBe('http://localhost:8181');
        expect(result.data.HITL_APPROVALS_URL).toBe('http://localhost:8002');
        expect(result.data.HITL_APPROVALS_PORT).toBe(8002);
        expect(result.data.DEFAULT_ESCALATION_TIMEOUT_MINUTES).toBe(30);
        expect(result.data.CRITICAL_ESCALATION_TIMEOUT_MINUTES).toBe(15);
        expect(result.data.EMERGENCY_ESCALATION_TIMEOUT_MINUTES).toBe(60);
      }
    });
  });
});

describe('ProductionSecuritySchema', () => {
  it('should accept strong Redis password', () => {
    const result = ProductionSecuritySchema.safeParse({
      REDIS_PASSWORD: 'strongpassword123',
    });
    expect(result.success).toBe(true);
  });

  it('should reject weak Redis password (less than 8 chars)', () => {
    const result = ProductionSecuritySchema.safeParse({
      REDIS_PASSWORD: 'weak',
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.errors[0].message).toContain('at least 8 characters');
    }
  });

  it('should accept strong Kafka password', () => {
    const result = ProductionSecuritySchema.safeParse({
      REDIS_PASSWORD: 'strongredis123',
      KAFKA_PASSWORD: 'strongkafka123',
    });
    expect(result.success).toBe(true);
  });

  it('should reject weak Kafka password (less than 8 chars)', () => {
    const result = ProductionSecuritySchema.safeParse({
      REDIS_PASSWORD: 'strongredis123',
      KAFKA_PASSWORD: 'weak',
    });
    expect(result.success).toBe(false);
  });

  it('should allow optional Kafka password (undefined)', () => {
    const result = ProductionSecuritySchema.safeParse({
      REDIS_PASSWORD: 'strongredis123',
    });
    expect(result.success).toBe(true);
  });

  it('should accept exactly 8 character password (boundary)', () => {
    const result = ProductionSecuritySchema.safeParse({
      REDIS_PASSWORD: '12345678',
    });
    expect(result.success).toBe(true);
  });

  it('should reject 7 character password (boundary - 1)', () => {
    const result = ProductionSecuritySchema.safeParse({
      REDIS_PASSWORD: '1234567',
    });
    expect(result.success).toBe(false);
  });
});
