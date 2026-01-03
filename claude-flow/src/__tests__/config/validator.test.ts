/**
 * Configuration Validation Tests
 *
 * Tests for the Zod-based configuration schema with security checks.
 */

import { configSchema } from "../../config/schema.js";

describe("Configuration Schema Validation", () => {
  // Save original env
  const originalEnv = process.env;

  beforeEach(() => {
    // Reset env before each test
    process.env = { ...originalEnv };
  });

  afterAll(() => {
    process.env = originalEnv;
  });

  describe("Valid Configurations", () => {
    it("should accept valid development configuration", () => {
      const config = {
        ENVIRONMENT: "development",
        TENANT_ID: "acgs-dev",
        REDIS_URL: "redis://localhost:6379/0",
        AGENT_BUS_URL: "http://localhost:8000",
        OPA_URL: "http://localhost:8181",
        LOG_LEVEL: "INFO",
        DEBUG: "true",
      };

      const result = configSchema.safeParse(config);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.ENVIRONMENT).toBe("development");
        expect(result.data.DEBUG).toBe(true);
      }
    });

    it("should accept valid production configuration", () => {
      const config = {
        ENVIRONMENT: "production",
        TENANT_ID: "acgs-prod",
        REDIS_URL: "rediss://redis.prod:6380/0",
        REDIS_PASSWORD: "secure-password-123",
        AGENT_BUS_URL: "https://agent-bus.prod:8000",
        OPA_URL: "https://opa.prod:8181",
        LOG_LEVEL: "WARN",
        DEBUG: "false",
        CRITICAL_ESCALATION_TIMEOUT_MINUTES: "15",
        DEFAULT_ESCALATION_TIMEOUT_MINUTES: "30",
      };

      const result = configSchema.safeParse(config);
      expect(result.success).toBe(true);
    });

    it("should apply default values for missing optional fields", () => {
      const config = {
        TENANT_ID: "test-tenant",
      };

      const result = configSchema.safeParse(config);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.ENVIRONMENT).toBe("development");
        expect(result.data.LOG_LEVEL).toBe("INFO");
        expect(result.data.DEBUG).toBe(false);
        expect(result.data.CONSTITUTIONAL_HASH).toBe("cdd01ef066bc6cf2");
      }
    });
  });

  describe("Security Policy Enforcement", () => {
    it("should reject DEBUG=true in production", () => {
      const config = {
        ENVIRONMENT: "production",
        REDIS_URL: "rediss://redis:6380",
        REDIS_PASSWORD: "password",
        DEBUG: "true",
        CRITICAL_ESCALATION_TIMEOUT_MINUTES: "15",
        DEFAULT_ESCALATION_TIMEOUT_MINUTES: "30",
      };

      const result = configSchema.safeParse(config);
      expect(result.success).toBe(false);
      if (!result.success) {
        const debugError = result.error.issues.find((i) => i.path.includes("DEBUG"));
        expect(debugError).toBeDefined();
        expect(debugError?.message).toContain("Security violation");
      }
    });

    it("should reject missing REDIS_PASSWORD in production", () => {
      const config = {
        ENVIRONMENT: "production",
        REDIS_URL: "rediss://redis:6380",
        DEBUG: "false",
        CRITICAL_ESCALATION_TIMEOUT_MINUTES: "15",
        DEFAULT_ESCALATION_TIMEOUT_MINUTES: "30",
      };

      const result = configSchema.safeParse(config);
      expect(result.success).toBe(false);
      if (!result.success) {
        const passwordError = result.error.issues.find((i) =>
          i.path.includes("REDIS_PASSWORD")
        );
        expect(passwordError).toBeDefined();
      }
    });

    it("should reject non-TLS Redis in production", () => {
      const config = {
        ENVIRONMENT: "production",
        REDIS_URL: "redis://redis:6379", // Should be rediss://
        REDIS_PASSWORD: "password",
        DEBUG: "false",
        CRITICAL_ESCALATION_TIMEOUT_MINUTES: "15",
        DEFAULT_ESCALATION_TIMEOUT_MINUTES: "30",
      };

      const result = configSchema.safeParse(config);
      expect(result.success).toBe(false);
      if (!result.success) {
        const tlsError = result.error.issues.find((i) =>
          i.message.includes("TLS")
        );
        expect(tlsError).toBeDefined();
      }
    });
  });

  describe("Type Validation", () => {
    it("should reject invalid URL format", () => {
      const config = {
        AGENT_BUS_URL: "not-a-url",
      };

      const result = configSchema.safeParse(config);
      expect(result.success).toBe(false);
    });

    it("should reject invalid Redis URL protocol", () => {
      const config = {
        REDIS_URL: "http://redis:6379", // Should be redis:// or rediss://
      };

      const result = configSchema.safeParse(config);
      expect(result.success).toBe(false);
    });

    it("should coerce string to number for port", () => {
      const config = {
        HITL_APPROVALS_PORT: "9000",
      };

      const result = configSchema.safeParse(config);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.HITL_APPROVALS_PORT).toBe(9000);
        expect(typeof result.data.HITL_APPROVALS_PORT).toBe("number");
      }
    });

    it("should reject invalid port range", () => {
      const config = {
        HITL_APPROVALS_PORT: "99999", // Max is 65535
      };

      const result = configSchema.safeParse(config);
      expect(result.success).toBe(false);
    });

    it("should coerce string to boolean for DEBUG", () => {
      const config = {
        DEBUG: "false",
      };

      const result = configSchema.safeParse(config);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.DEBUG).toBe(false);
        expect(typeof result.data.DEBUG).toBe("boolean");
      }
    });
  });

  describe("Timeout Validation", () => {
    it("should reject timeout below minimum", () => {
      const config = {
        DEFAULT_ESCALATION_TIMEOUT_MINUTES: "0",
      };

      const result = configSchema.safeParse(config);
      expect(result.success).toBe(false);
    });

    it("should reject timeout above maximum (24 hours)", () => {
      const config = {
        DEFAULT_ESCALATION_TIMEOUT_MINUTES: "1500", // Max is 1440
      };

      const result = configSchema.safeParse(config);
      expect(result.success).toBe(false);
    });

    it("should reject CRITICAL timeout >= DEFAULT timeout", () => {
      const config = {
        CRITICAL_ESCALATION_TIMEOUT_MINUTES: "30",
        DEFAULT_ESCALATION_TIMEOUT_MINUTES: "30", // Should be less than
      };

      const result = configSchema.safeParse(config);
      expect(result.success).toBe(false);
      if (!result.success) {
        const timeoutError = result.error.issues.find((i) =>
          i.message.includes("shorter")
        );
        expect(timeoutError).toBeDefined();
      }
    });
  });

  describe("Tenant ID Validation", () => {
    it("should accept valid alphanumeric tenant ID", () => {
      const validIds = ["acgs-dev", "tenant_123", "MyTenant", "test-tenant-1"];

      validIds.forEach((id) => {
        const result = configSchema.safeParse({ TENANT_ID: id });
        expect(result.success).toBe(true);
      });
    });

    it("should reject tenant ID with special characters", () => {
      const config = {
        TENANT_ID: "tenant@invalid!",
      };

      const result = configSchema.safeParse(config);
      expect(result.success).toBe(false);
    });

    it("should reject empty tenant ID", () => {
      const config = {
        TENANT_ID: "",
      };

      const result = configSchema.safeParse(config);
      expect(result.success).toBe(false);
    });
  });

  describe("Log Level Validation", () => {
    it("should accept valid RFC 5424 log levels", () => {
      const validLevels = ["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"];

      validLevels.forEach((level) => {
        const result = configSchema.safeParse({ LOG_LEVEL: level });
        expect(result.success).toBe(true);
      });
    });

    it("should reject invalid log level", () => {
      const config = {
        LOG_LEVEL: "TRACE", // Not a valid level
      };

      const result = configSchema.safeParse(config);
      expect(result.success).toBe(false);
    });
  });

  describe("Constitutional Hash Validation", () => {
    it("should accept valid 16-character hash", () => {
      const config = {
        CONSTITUTIONAL_HASH: "abcd1234efgh5678",
      };

      const result = configSchema.safeParse(config);
      expect(result.success).toBe(true);
    });

    it("should reject hash with wrong length", () => {
      const config = {
        CONSTITUTIONAL_HASH: "tooshort",
      };

      const result = configSchema.safeParse(config);
      expect(result.success).toBe(false);
    });
  });

  describe("Memory Service Configuration", () => {
    it("should accept valid TTL values", () => {
      const config = {
        MEMORY_DEFAULT_TTL_SECONDS: "3600", // 1 hour
      };

      const result = configSchema.safeParse(config);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.MEMORY_DEFAULT_TTL_SECONDS).toBe(3600);
      }
    });

    it("should reject TTL below minimum", () => {
      const config = {
        MEMORY_DEFAULT_TTL_SECONDS: "30", // Min is 60
      };

      const result = configSchema.safeParse(config);
      expect(result.success).toBe(false);
    });

    it("should reject TTL above maximum (30 days)", () => {
      const config = {
        MEMORY_DEFAULT_TTL_SECONDS: "3000000", // Max is 2592000 (30 days)
      };

      const result = configSchema.safeParse(config);
      expect(result.success).toBe(false);
    });
  });
});
