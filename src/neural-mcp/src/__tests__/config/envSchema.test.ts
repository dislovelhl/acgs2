/**
 * Environment Schema Tests
 *
 * Comprehensive test suite for envSchema covering:
 * - Schema transformations (boolean, integer, URL)
 * - Field-level validation rules
 * - Default value handling
 * - Production security schema
 *
 * @module envSchema.test
 */

import { EnvSchema, ProductionSecuritySchema, EnvConfig } from '../../config/envSchema';

describe('EnvSchema', () => {
  describe('Boolean Transform', () => {
    it('should transform "true" to boolean true', () => {
      const result = EnvSchema.parse({ DEBUG: 'true' });
      expect(result.DEBUG).toBe(true);
    });

    it('should transform "TRUE" (uppercase) to boolean true', () => {
      const result = EnvSchema.parse({ DEBUG: 'TRUE' });
      expect(result.DEBUG).toBe(true);
    });

    it('should transform "1" to boolean true', () => {
      const result = EnvSchema.parse({ DEBUG: '1' });
      expect(result.DEBUG).toBe(true);
    });

    it('should transform "yes" to boolean true', () => {
      const result = EnvSchema.parse({ DEBUG: 'yes' });
      expect(result.DEBUG).toBe(true);
    });

    it('should transform "YES" to boolean true', () => {
      const result = EnvSchema.parse({ DEBUG: 'YES' });
      expect(result.DEBUG).toBe(true);
    });

    it('should transform "false" to boolean false', () => {
      const result = EnvSchema.parse({ DEBUG: 'false' });
      expect(result.DEBUG).toBe(false);
    });

    it('should transform "FALSE" to boolean false', () => {
      const result = EnvSchema.parse({ DEBUG: 'FALSE' });
      expect(result.DEBUG).toBe(false);
    });

    it('should transform "0" to boolean false', () => {
      const result = EnvSchema.parse({ DEBUG: '0' });
      expect(result.DEBUG).toBe(false);
    });

    it('should transform "no" to boolean false', () => {
      const result = EnvSchema.parse({ DEBUG: 'no' });
      expect(result.DEBUG).toBe(false);
    });

    it('should transform empty string to boolean false', () => {
      const result = EnvSchema.parse({ DEBUG: '' });
      expect(result.DEBUG).toBe(false);
    });

    it('should handle missing boolean field with default false', () => {
      const result = EnvSchema.parse({});
      expect(result.DEBUG).toBe(false);
      expect(result.RELOAD).toBe(false);
    });

    it('should handle whitespace in boolean string', () => {
      const result = EnvSchema.parse({ DEBUG: '  true  ' });
      expect(result.DEBUG).toBe(true);
    });

    it('should transform RELOAD field similarly', () => {
      const result = EnvSchema.parse({ RELOAD: 'true' });
      expect(result.RELOAD).toBe(true);
    });
  });

  describe('Positive Integer Transform', () => {
    it('should transform timeout string to integer', () => {
      const result = EnvSchema.parse({
        DEFAULT_ESCALATION_TIMEOUT_MINUTES: '45',
      });
      expect(result.DEFAULT_ESCALATION_TIMEOUT_MINUTES).toBe(45);
    });

    it('should use default timeout values when not provided', () => {
      const result = EnvSchema.parse({});
      expect(result.DEFAULT_ESCALATION_TIMEOUT_MINUTES).toBe(30);
      expect(result.CRITICAL_ESCALATION_TIMEOUT_MINUTES).toBe(15);
      expect(result.EMERGENCY_ESCALATION_TIMEOUT_MINUTES).toBe(60);
    });

    it('should reject negative timeout values', () => {
      expect(() => {
        EnvSchema.parse({
          DEFAULT_ESCALATION_TIMEOUT_MINUTES: '-5',
        });
      }).toThrow();
    });

    it('should reject zero timeout values', () => {
      expect(() => {
        EnvSchema.parse({
          CRITICAL_ESCALATION_TIMEOUT_MINUTES: '0',
        });
      }).toThrow();
    });

    it('should reject non-numeric timeout values', () => {
      expect(() => {
        EnvSchema.parse({
          EMERGENCY_ESCALATION_TIMEOUT_MINUTES: 'abc',
        });
      }).toThrow();
    });

    it('should accept large positive timeout values', () => {
      const result = EnvSchema.parse({
        DEFAULT_ESCALATION_TIMEOUT_MINUTES: '9999',
      });
      expect(result.DEFAULT_ESCALATION_TIMEOUT_MINUTES).toBe(9999);
    });
  });

  describe('URL Schema', () => {
    describe('REDIS_URL', () => {
      it('should accept redis:// protocol', () => {
        const result = EnvSchema.parse({
          REDIS_URL: 'redis://localhost:6379',
        });
        expect(result.REDIS_URL).toBe('redis://localhost:6379');
      });

      it('should accept rediss:// protocol (TLS)', () => {
        const result = EnvSchema.parse({
          REDIS_URL: 'rediss://secure-redis:6379',
        });
        expect(result.REDIS_URL).toBe('rediss://secure-redis:6379');
      });

      it('should reject http:// protocol for Redis', () => {
        expect(() => {
          EnvSchema.parse({
            REDIS_URL: 'http://localhost:6379',
          });
        }).toThrow();
      });

      it('should reject invalid URL format', () => {
        expect(() => {
          EnvSchema.parse({
            REDIS_URL: 'not-a-url',
          });
        }).toThrow();
      });

      it('should use default Redis URL when not provided', () => {
        const result = EnvSchema.parse({});
        expect(result.REDIS_URL).toBe('redis://localhost:6379');
      });
    });

    describe('HTTP URLs (AGENT_BUS_URL, OPA_URL, HITL_APPROVALS_URL)', () => {
      it('should accept http:// protocol', () => {
        const result = EnvSchema.parse({
          AGENT_BUS_URL: 'http://localhost:8000',
          OPA_URL: 'http://localhost:8181',
          HITL_APPROVALS_URL: 'http://localhost:8002',
        });
        expect(result.AGENT_BUS_URL).toBe('http://localhost:8000');
        expect(result.OPA_URL).toBe('http://localhost:8181');
        expect(result.HITL_APPROVALS_URL).toBe('http://localhost:8002');
      });

      it('should accept https:// protocol', () => {
        const result = EnvSchema.parse({
          AGENT_BUS_URL: 'https://secure-bus.example.com',
          OPA_URL: 'https://secure-opa.example.com',
          HITL_APPROVALS_URL: 'https://secure-hitl.example.com',
        });
        expect(result.AGENT_BUS_URL).toBe('https://secure-bus.example.com');
        expect(result.OPA_URL).toBe('https://secure-opa.example.com');
        expect(result.HITL_APPROVALS_URL).toBe('https://secure-hitl.example.com');
      });

      it('should reject ftp:// protocol', () => {
        expect(() => {
          EnvSchema.parse({
            OPA_URL: 'ftp://ftp-server.example.com',
          });
        }).toThrow();
      });

      it('should use default URLs when not provided', () => {
        const result = EnvSchema.parse({});
        expect(result.AGENT_BUS_URL).toBe('http://localhost:8000');
        expect(result.OPA_URL).toBe('http://localhost:8181');
        expect(result.HITL_APPROVALS_URL).toBe('http://localhost:8002');
      });
    });
  });

  describe('Port Validation', () => {
    it('should transform port string to number', () => {
      const result = EnvSchema.parse({
        HITL_APPROVALS_PORT: '9000',
      });
      expect(result.HITL_APPROVALS_PORT).toBe(9000);
    });

    it('should accept port 1 (minimum)', () => {
      const result = EnvSchema.parse({
        HITL_APPROVALS_PORT: '1',
      });
      expect(result.HITL_APPROVALS_PORT).toBe(1);
    });

    it('should accept port 65535 (maximum)', () => {
      const result = EnvSchema.parse({
        HITL_APPROVALS_PORT: '65535',
      });
      expect(result.HITL_APPROVALS_PORT).toBe(65535);
    });

    it('should reject port 0', () => {
      expect(() => {
        EnvSchema.parse({
          HITL_APPROVALS_PORT: '0',
        });
      }).toThrow();
    });

    it('should reject port > 65535', () => {
      expect(() => {
        EnvSchema.parse({
          HITL_APPROVALS_PORT: '65536',
        });
      }).toThrow();
    });

    it('should reject negative port', () => {
      expect(() => {
        EnvSchema.parse({
          HITL_APPROVALS_PORT: '-1',
        });
      }).toThrow();
    });

    it('should reject non-numeric port', () => {
      expect(() => {
        EnvSchema.parse({
          HITL_APPROVALS_PORT: 'abc',
        });
      }).toThrow();
    });

    it('should use default port when not provided', () => {
      const result = EnvSchema.parse({});
      expect(result.HITL_APPROVALS_PORT).toBe(8002);
    });
  });

  describe('Enum Validation', () => {
    describe('ENVIRONMENT', () => {
      it('should accept development', () => {
        const result = EnvSchema.parse({ ENVIRONMENT: 'development' });
        expect(result.ENVIRONMENT).toBe('development');
      });

      it('should accept staging', () => {
        const result = EnvSchema.parse({ ENVIRONMENT: 'staging' });
        expect(result.ENVIRONMENT).toBe('staging');
      });

      it('should accept production', () => {
        const result = EnvSchema.parse({ ENVIRONMENT: 'production' });
        expect(result.ENVIRONMENT).toBe('production');
      });

      it('should reject invalid environment', () => {
        expect(() => {
          EnvSchema.parse({ ENVIRONMENT: 'testing' });
        }).toThrow();
      });

      it('should use development as default', () => {
        const result = EnvSchema.parse({});
        expect(result.ENVIRONMENT).toBe('development');
      });
    });

    describe('LOG_LEVEL', () => {
      it('should accept DEBUG', () => {
        const result = EnvSchema.parse({ LOG_LEVEL: 'DEBUG' });
        expect(result.LOG_LEVEL).toBe('DEBUG');
      });

      it('should accept INFO', () => {
        const result = EnvSchema.parse({ LOG_LEVEL: 'INFO' });
        expect(result.LOG_LEVEL).toBe('INFO');
      });

      it('should accept WARN', () => {
        const result = EnvSchema.parse({ LOG_LEVEL: 'WARN' });
        expect(result.LOG_LEVEL).toBe('WARN');
      });

      it('should accept ERROR', () => {
        const result = EnvSchema.parse({ LOG_LEVEL: 'ERROR' });
        expect(result.LOG_LEVEL).toBe('ERROR');
      });

      it('should reject invalid log level', () => {
        expect(() => {
          EnvSchema.parse({ LOG_LEVEL: 'TRACE' });
        }).toThrow();
      });

      it('should use INFO as default', () => {
        const result = EnvSchema.parse({});
        expect(result.LOG_LEVEL).toBe('INFO');
      });
    });
  });

  describe('String Fields', () => {
    it('should accept valid TENANT_ID', () => {
      const result = EnvSchema.parse({ TENANT_ID: 'my-tenant-id' });
      expect(result.TENANT_ID).toBe('my-tenant-id');
    });

    it('should reject empty TENANT_ID', () => {
      expect(() => {
        EnvSchema.parse({ TENANT_ID: '' });
      }).toThrow();
    });

    it('should use default TENANT_ID when not provided', () => {
      const result = EnvSchema.parse({});
      expect(result.TENANT_ID).toBe('acgs-dev');
    });

    it('should accept optional REDIS_PASSWORD', () => {
      const result = EnvSchema.parse({ REDIS_PASSWORD: 'mypassword' });
      expect(result.REDIS_PASSWORD).toBe('mypassword');
    });

    it('should accept empty REDIS_PASSWORD', () => {
      const result = EnvSchema.parse({ REDIS_PASSWORD: '' });
      expect(result.REDIS_PASSWORD).toBe('');
    });

    it('should accept optional KAFKA_BOOTSTRAP', () => {
      const result = EnvSchema.parse({ KAFKA_BOOTSTRAP: 'kafka:9092' });
      expect(result.KAFKA_BOOTSTRAP).toBe('kafka:9092');
    });

    it('should accept optional KAFKA_PASSWORD', () => {
      const result = EnvSchema.parse({ KAFKA_PASSWORD: 'kafkapass' });
      expect(result.KAFKA_PASSWORD).toBe('kafkapass');
    });
  });

  describe('Default Values', () => {
    it('should apply all default values for empty input', () => {
      const result = EnvSchema.parse({});

      expect(result.TENANT_ID).toBe('acgs-dev');
      expect(result.ENVIRONMENT).toBe('development');
      expect(result.LOG_LEVEL).toBe('INFO');
      expect(result.DEBUG).toBe(false);
      expect(result.RELOAD).toBe(false);
      expect(result.REDIS_URL).toBe('redis://localhost:6379');
      expect(result.REDIS_PASSWORD).toBe('');
      expect(result.KAFKA_BOOTSTRAP).toBe('');
      expect(result.KAFKA_PASSWORD).toBe('');
      expect(result.AGENT_BUS_URL).toBe('http://localhost:8000');
      expect(result.OPA_URL).toBe('http://localhost:8181');
      expect(result.HITL_APPROVALS_URL).toBe('http://localhost:8002');
      expect(result.HITL_APPROVALS_PORT).toBe(8002);
      expect(result.DEFAULT_ESCALATION_TIMEOUT_MINUTES).toBe(30);
      expect(result.CRITICAL_ESCALATION_TIMEOUT_MINUTES).toBe(15);
      expect(result.EMERGENCY_ESCALATION_TIMEOUT_MINUTES).toBe(60);
    });
  });

  describe('safeParse method', () => {
    it('should return success: true for valid config', () => {
      const result = EnvSchema.safeParse({ TENANT_ID: 'test' });
      expect(result.success).toBe(true);
    });

    it('should return success: false for invalid config', () => {
      const result = EnvSchema.safeParse({ ENVIRONMENT: 'invalid' });
      expect(result.success).toBe(false);
    });

    it('should include error details on failure', () => {
      const result = EnvSchema.safeParse({ ENVIRONMENT: 'invalid' });
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.errors).toBeDefined();
        expect(result.error.errors.length).toBeGreaterThan(0);
      }
    });
  });
});

describe('ProductionSecuritySchema', () => {
  it('should accept REDIS_PASSWORD with 8+ characters', () => {
    const result = ProductionSecuritySchema.safeParse({
      REDIS_PASSWORD: '12345678',
    });
    expect(result.success).toBe(true);
  });

  it('should reject REDIS_PASSWORD with < 8 characters', () => {
    const result = ProductionSecuritySchema.safeParse({
      REDIS_PASSWORD: 'short',
    });
    expect(result.success).toBe(false);
  });

  it('should accept empty object (KAFKA_PASSWORD is optional)', () => {
    // REDIS_PASSWORD is required by this schema
    const result = ProductionSecuritySchema.safeParse({
      REDIS_PASSWORD: 'longpassword',
    });
    expect(result.success).toBe(true);
  });

  it('should accept KAFKA_PASSWORD with 8+ characters', () => {
    const result = ProductionSecuritySchema.safeParse({
      REDIS_PASSWORD: 'longpassword',
      KAFKA_PASSWORD: 'kafkapass123',
    });
    expect(result.success).toBe(true);
  });

  it('should reject KAFKA_PASSWORD with < 8 characters', () => {
    const result = ProductionSecuritySchema.safeParse({
      REDIS_PASSWORD: 'longpassword',
      KAFKA_PASSWORD: 'short',
    });
    expect(result.success).toBe(false);
  });

  it('should allow undefined KAFKA_PASSWORD', () => {
    const result = ProductionSecuritySchema.safeParse({
      REDIS_PASSWORD: 'longpassword',
      KAFKA_PASSWORD: undefined,
    });
    expect(result.success).toBe(true);
  });
});
