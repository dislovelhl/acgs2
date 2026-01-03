import { configSchema, Config } from "./schema";
import dotenv from "dotenv";

dotenv.config();

export function validateConfig(): Config {
  const result = configSchema.safeParse(process.env);

  if (!result.success) {
    console.error("❌ MCP Configuration validation failed!");
    result.error.issues.forEach((issue) => {
      console.error(`   • [${issue.path.join(".")}] ${issue.message}`);
    });
    process.exit(1);
  }

  return result.data;
}

const config = validateConfig();
export default config;
