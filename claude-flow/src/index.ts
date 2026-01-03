#!/usr/bin/env node

import { Command } from "commander";
import chalk from "chalk";
import "./config";
import { agentCommand } from "./commands/agent";
import { swarmCommand } from "./commands/swarm";
import { analyzeCommand } from "./commands/analyze";
import { taskCommand } from "./commands/task";
import { coordinationCommand } from "./commands/coordination";

const program = new Command();

// Initialize MemoryService (non-blocking - CLI works even if Redis unavailable)
const memoryService = getMemoryService();
memoryService.initialize().catch((error) => {
  // Silently continue - MemoryService will operate in degraded mode
  // Commands that require memory will check connection state
  if (process.env.DEBUG === 'true') {
    process.stderr.write(chalk.yellow(`[MemoryService] Redis unavailable: ${error.message}\n`));
  }
});

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

// Graceful shutdown handler for MemoryService
const gracefulShutdown = async (signal: string): Promise<void> => {
  if (memoryService.isConnected()) {
    await memoryService.disconnect();
  }
  process.exit(0);
};

process.on('SIGINT', () => gracefulShutdown('SIGINT'));
process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));

program.parse();
