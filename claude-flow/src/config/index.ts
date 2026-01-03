/**
 * Configuration Loader - Fail-fast validation with remediation guidance
 *
 * This module loads and validates configuration at startup, providing:
 * - Immediate exit on invalid configuration
 * - Clear error messages with remediation steps
 * - Security policy enforcement
 *
 * @module config
 */

import dotenv from "dotenv";
import { configSchema, Config, ValidationError, ValidationResult } from "./schema.js";
import chalk from "chalk";

// Load .env file from current directory and parent
dotenv.config();
dotenv.config({ path: "../.env" });

/**
 * Remediation guidance for common configuration errors
 */
const REMEDIATION_GUIDE: Record<string, string> = {
  "DEBUG": "Set DEBUG=false in your production .env file.",
  "REDIS_PASSWORD": "Set a strong REDIS_PASSWORD (min 8 characters) in your .env file.",
  "REDIS_URL": "Update REDIS_URL to use rediss:// protocol for TLS in production.",
  "TENANT_ID": "Set TENANT_ID to a valid alphanumeric identifier (e.g., 'acgs-prod').",
  "CRITICAL_ESCALATION_TIMEOUT_MINUTES": "Set CRITICAL_ESCALATION_TIMEOUT_MINUTES to a value less than DEFAULT_ESCALATION_TIMEOUT_MINUTES.",
  "CONSTITUTIONAL_HASH": "Do not modify CONSTITUTIONAL_HASH unless updating the constitutional compliance version.",
};

/**
 * Get remediation guidance for a configuration field
 */
function getRemediation(field: string, code: string): string {
  if (REMEDIATION_GUIDE[field]) {
    return REMEDIATION_GUIDE[field];
  }

  switch (code) {
    case "invalid_type":
      return `Ensure ${field} has the correct type in your .env file.`;
    case "too_small":
    case "too_big":
      return `Adjust the value of ${field} to be within the allowed range.`;
    case "invalid_string":
      return `Check that ${field} matches the required format.`;
    case "invalid_enum_value":
      return `Set ${field} to one of the allowed values.`;
    default:
      return `Check your .env file and ensure ${field} is correctly configured.`;
  }
}

/**
 * Validate configuration and return structured result
 *
 * Use this for programmatic validation without exiting.
 */
export function validateConfigSafe(): ValidationResult {
  const result = configSchema.safeParse(process.env);

  if (result.success) {
    return {
      valid: true,
      config: result.data,
      errors: [],
    };
  }

  const errors: ValidationError[] = result.error.issues.map((issue) => {
    const field = issue.path.join(".");
    return {
      field,
      message: issue.message,
      code: issue.code,
      remediation: getRemediation(field, issue.code),
    };
  });

  return {
    valid: false,
    errors,
  };
}

/**
 * Validate configuration with fail-fast behavior
 *
 * Exits the process immediately if configuration is invalid.
 * This ensures the application never runs with bad configuration.
 */
export function validateConfig(): Config {
  const result = validateConfigSafe();

  if (!result.valid) {
    console.error(chalk.red.bold("\n❌ Configuration validation failed!\n"));
    console.error(chalk.red("The application cannot start with invalid configuration.\n"));

    result.errors.forEach((error, index) => {
      console.error(chalk.yellow(`${index + 1}. [${error.field}] ${error.message}`));
      console.log(chalk.blue(`   💡 Remediation: ${error.remediation}\n`));
    });

    console.log(chalk.gray("─".repeat(60)));
    console.log(chalk.gray("For more information, see docs/CONFIGURATION_TROUBLESHOOTING.md"));
    console.log(chalk.gray("or run: claude-flow config --validate"));
    console.log(chalk.gray("─".repeat(60) + "\n"));

    process.exit(1);
  }

  // Log successful validation in development
  if (result.config!.ENVIRONMENT === "development") {
    console.log(chalk.green("✓ Configuration validated successfully"));
    console.log(chalk.gray(`  Environment: ${result.config!.ENVIRONMENT}`));
    console.log(chalk.gray(`  Tenant: ${result.config!.TENANT_ID}`));
    console.log(chalk.gray(`  Log Level: ${result.config!.LOG_LEVEL}`));
  }

  return result.config!;
}

/**
 * Export types for use in other modules
 */
export type { Config, ValidationError, ValidationResult };
export { configSchema } from "./schema.js";

// Validate and export config singleton
const config = validateConfig();
export default config;
