import { configSchema } from "../../config/schema";

describe("MCP Configuration Validation", () => {
  it("should validate a correct configuration", () => {
    const validConfig = {
      MCP_NAME: "test-mcp",
      MCP_VERSION: "1.2.3",
      NEURAL_EPOCHS: "50",
    };

    const result = configSchema.safeParse(validConfig);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.MCP_NAME).toBe("test-mcp");
      expect(result.data.NEURAL_EPOCHS).toBe(50);
    }
  });

  it("should use default values for missing fields", () => {
    const emptyConfig = {};
    const result = configSchema.safeParse(emptyConfig);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.MCP_NAME).toBe("acgs2-neural-mcp");
      expect(result.data.NEURAL_EPOCHS).toBe(100);
    }
  });

  it("should fail on invalid NEURAL_EPOCHS", () => {
    const invalidConfig = {
      NEURAL_EPOCHS: "not-a-number",
    };
    const result = configSchema.safeParse(invalidConfig);
    expect(result.success).toBe(false);
  });
});
