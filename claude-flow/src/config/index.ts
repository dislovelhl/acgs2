import dotenv from "dotenv";
import { configSchema, Config } from "./schema";
import chalk from "chalk";

// Load .env file
dotenv.config();

export function validateConfig(): Config {
  const result = configSchema.safeParse(process.env);

  if (!result.success) {
    console.error(chalk.red("❌ Configuration validation failed!"));

    result.error.issues.forEach((issue) => {
      const path = issue.path.join(".");
      console.error(chalk.yellow(`   • [${path}] ${issue.message}`));

      // Remediation guidance
      if (path === "DEBUG" && issue.message.includes("production")) {
        console.log(
          chalk.blue(
            "     💡 Fix: Set DEBUG=false in .env for production environments."
          )
        );
      } else if (issue.code === "invalid_type") {
        console.log(
          chalk.blue(
            `     💡 Fix: Ensure ${path} has the correct type in your .env file.`
          )
        );
      } else if (issue.code === "too_small" || issue.code === "too_big") {
        console.log(
          chalk.blue(
            `     💡 Fix: Adjust the value of ${path} to be within the allowed range.`
          )
        );
      }
    });

    console.log(
      chalk.gray(
        "\nFor more information, see DOCUMENTATION.md or contact the ACGS-2 team."
      )
    );
    process.exit(1);
  }

  return result.data;
}

const config = validateConfig();
export default config;
