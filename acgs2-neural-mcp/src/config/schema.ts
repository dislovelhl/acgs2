import { z } from "zod";

export const configSchema = z.object({
  MCP_NAME: z.string().default("acgs2-neural-mcp"),
  MCP_VERSION: z.string().default("2.0.0"),
  LOG_LEVEL: z.enum(["DEBUG", "INFO", "WARN", "ERROR"]).default("INFO"),
  NEURAL_EPOCHS: z.coerce.number().int().positive().default(100),
  NEURAL_LEARNING_RATE: z.coerce.number().positive().default(0.001),
  CONSTITUTIONAL_HASH: z.string().length(16).default("cdd01ef066bc6cf2"),
});

export type Config = z.infer<typeof configSchema>;
