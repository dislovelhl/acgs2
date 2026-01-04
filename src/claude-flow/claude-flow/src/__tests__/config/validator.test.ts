import { configSchema } from "../../config/schema";

describe("Configuration Validation", () => {
  it("should validate a correct configuration", () => {
    const validConfig = {
      ENVIRONMENT: "development",
      TENANT_ID: "test-tenant",
      REDIS_URL: "redis://localhost:6379/0",
      DEBUG: "true",
    };

    const result = configSchema.safeParse(validConfig);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.ENVIRONMENT).toBe("development");
      expect(result.data.DEBUG).toBe(true);
    }
  });

  it("should fail if DEBUG is true in production", () => {
    const invalidConfig = {
      ENVIRONMENT: "production",
      DEBUG: "true",
    };

    const result = configSchema.safeParse(invalidConfig);
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0].message).toBe(
        "DEBUG mode cannot be enabled in production"
      );
    }
  });

  it("should use default values for missing fields", () => {
    const emptyConfig = {};
    const result = configSchema.safeParse(emptyConfig);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.ENVIRONMENT).toBe("development");
      expect(result.data.TENANT_ID).toBe("acgs-dev");
    }
  });

  it("should fail on invalid REDIS_URL", () => {
    const invalidConfig = {
      REDIS_URL: "not-a-url",
    };
    const result = configSchema.safeParse(invalidConfig);
    expect(result.success).toBe(false);
  });
});
