#!/usr/bin/env node

import { Command } from "commander";
import chalk from "chalk";
import "./config";
import { agentCommand } from "./commands/agent";
import { swarmCommand } from "./commands/swarm";
import { analyzeCommand } from "./commands/analyze";
import { taskCommand } from "./commands/task";
import { coordinationCommand } from "./commands/coordination";
import { memoryService } from "./services/memory";
import { logger } from "./utils/logger";

const program = new Command();

program
  .name("claude-flow")
  .description("CLI tool for managing ACGS-2 agent swarms")
  .version("1.0.0");

// Add agent command
program.addCommand(agentCommand);

// Add swarm command
program.addCommand(swarmCommand);

// Add analyze command
program.addCommand(analyzeCommand);

// Add task command
program.addCommand(taskCommand);

// Add coordination command
program.addCommand(coordinationCommand);

// Handle unhandled promise rejections
process.on("unhandledRejection", (error) => {
  console.error(chalk.red("Unhandled promise rejection:"), error);
  process.exit(1);
});

// Handle uncaught exceptions
process.on("uncaughtException", (error) => {
  console.error(chalk.red("Uncaught exception:"), error);
  process.exit(1);
});

// Handle graceful shutdown
const shutdown = async () => {
  logger.info("Shutting down...");
  await memoryService.disconnect();
  process.exit(0);
};

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);

async function main() {
  try {
    // Initialize memory service
    await memoryService.initialize();

    // Parse command line arguments
    program.parse(process.argv);
  } catch (error) {
    logger.error("Initialization failed", error);
    process.exit(1);
  }
}

main();
