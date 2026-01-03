import { z } from "zod";

export const environmentSchema = z.enum([
  "development",
  "staging",
  "production",
  "test",
  "ci",
]);

export const configSchema = z
  .object({
    ENVIRONMENT: environmentSchema.default("development"),
    TENANT_ID: z.string().default("acgs-dev"),
    REDIS_URL: z.string().url().default("redis://localhost:6379/0"),
    REDIS_PASSWORD: z.string().optional(),
    KAFKA_BOOTSTRAP: z.string().optional(),
    KAFKA_PASSWORD: z.string().optional(),
    AGENT_BUS_URL: z.string().url().default("http://localhost:8000"),
    OPA_URL: z.string().url().default("http://localhost:8181"),
    HITL_APPROVALS_PORT: z.coerce.number().int().positive().default(8003),
    HITL_APPROVALS_URL: z.string().url().default("http://localhost:8003"),
    LOG_LEVEL: z.enum(["DEBUG", "INFO", "WARN", "ERROR"]).default("INFO"),
    DEBUG: z.coerce.boolean().default(false),
    RELOAD: z.coerce.boolean().default(false),
    CONSTITUTIONAL_HASH: z.string().length(16).default("cdd01ef066bc6cf2"),
  })
  .refine(
    (data) => {
      if (data.ENVIRONMENT === "production" && data.DEBUG === true) {
        return false;
      }
      return true;
    },
    {
      message: "DEBUG mode cannot be enabled in production",
      path: ["DEBUG"],
    }
  );

export type Config = z.infer<typeof configSchema>;
