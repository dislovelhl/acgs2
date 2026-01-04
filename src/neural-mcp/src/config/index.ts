import { configSchema, Config } from "./schema";
import dotenv from "dotenv";
import chalk from "chalk";

dotenv.config();

export function validateConfig(): Config {
  const result = configSchema.safeParse(process.env);

  if (!result.success) {
    console.error(chalk.red("❌ MCP Configuration validation failed!"));

    result.error.issues.forEach((issue) => {
      const path = issue.path.join(".");
      console.error(chalk.yellow(`   • [${path}] ${issue.message}`));

      // Remediation guidance
      if (issue.code === "invalid_type") {
        console.log(
          chalk.blue(
            `     💡 Fix: Ensure ${path} has the correct type in your environment.`
          )
        );
      } else if (issue.code === "too_small" || issue.code === "too_big") {
        console.log(
          chalk.blue(
            `     💡 Fix: Adjust the value of ${path} to be within the allowed range.`
          )
        );
      } else {
        console.log(
          chalk.blue(
            `     💡 Fix: Check the value of ${path} in your environment variables.`
          )
        );
      }
    });

    console.log(
      chalk.gray(
        "\nFor more information, see the MCP documentation."
      )
    );
    process.exit(1);
  }

  return result.data;
}

const config = validateConfig();
export default config;
