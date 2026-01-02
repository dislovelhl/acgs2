import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import { orchestrateTask } from '../services/taskService';
import { getLogger, cliOutput } from '../utils/logging_config';

// Initialize logger for this module
const logger = getLogger('commands/task');

export const taskCommand = new Command('task')
  .description('Manage task orchestration across the swarm');

// Valid orchestration strategies
const VALID_STRATEGIES = ['sequential', 'parallel', 'hierarchical', 'consensus'] as const;
type OrchestrationStrategy = typeof VALID_STRATEGIES[number];

// Valid priority levels
const VALID_PRIORITIES = ['low', 'medium', 'high', 'critical'] as const;
type PriorityLevel = typeof VALID_PRIORITIES[number];

function validateStrategy(strategy: string): strategy is OrchestrationStrategy {
  return VALID_STRATEGIES.includes(strategy as OrchestrationStrategy);
}

function validatePriority(priority: string): priority is PriorityLevel {
  return VALID_PRIORITIES.includes(priority as PriorityLevel);
}

const orchestrateCommand = new Command('orchestrate')
  .description('Orchestrate complex tasks across the swarm')
  .requiredOption('-t, --task <description>', 'Task description')
  .option('-s, --strategy <type>', `Orchestration strategy (${VALID_STRATEGIES.join(', ')})`, 'parallel')
  .option('-p, --priority <level>', `Task priority (${VALID_PRIORITIES.join(', ')})`, 'medium')
  .action(async (options) => {
    const spinner = ora('Validating orchestration parameters...').start();

    try {
      // Validate strategy
      if (!validateStrategy(options.strategy)) {
        spinner.fail(chalk.red(`❌ Invalid orchestration strategy: ${options.strategy}`));
        logger.warn('invalid_orchestration_strategy', { strategy: options.strategy });
        cliOutput(chalk.yellow(`\n📋 Valid strategies: ${VALID_STRATEGIES.join(', ')}`));
        cliOutput(chalk.gray(`\n  sequential: Tasks executed one after another`));
        cliOutput(chalk.gray(`  parallel: Tasks executed simultaneously`));
        cliOutput(chalk.gray(`  hierarchical: Coordinator oversees specialized agents`));
        cliOutput(chalk.gray(`  consensus: Multiple agents vote on approach`));
        cliOutput(chalk.gray(`\nExample: npx claude-flow task orchestrate --task "Implement authentication" --strategy parallel`));
        process.exit(1);
      }

      // Validate priority
      if (!validatePriority(options.priority)) {
        spinner.fail(chalk.red(`❌ Invalid priority level: ${options.priority}`));
        logger.warn('invalid_priority_level', { priority: options.priority });
        cliOutput(chalk.yellow(`\n📋 Valid priorities: ${VALID_PRIORITIES.join(', ')}`));
        cliOutput(chalk.gray(`\n  low: Standard processing time`));
        cliOutput(chalk.gray(`  medium: Moderate priority (default)`));
        cliOutput(chalk.gray(`  high: Expedited processing`));
        cliOutput(chalk.gray(`  critical: Immediate attention required`));
        cliOutput(chalk.gray(`\nExample: npx claude-flow task orchestrate --task "Fix production bug" --priority critical`));
        process.exit(1);
      }

      // Validate task description
      if (!options.task || options.task.trim().length === 0) {
        spinner.fail(chalk.red(`❌ Task description cannot be empty`));
        logger.warn('empty_task_description');
        cliOutput(chalk.yellow(`\n💡 Provide a clear, actionable task description`));
        cliOutput(chalk.gray(`\nExample: npx claude-flow task orchestrate --task "Implement user authentication system"`));
        process.exit(1);
      }

      if (options.task.trim().length < 10) {
        spinner.fail(chalk.red(`❌ Task description too short: ${options.task.trim().length} characters`));
        logger.warn('task_description_too_short', { length: options.task.trim().length });
        cliOutput(chalk.yellow(`\n💡 Task descriptions should be detailed enough for agents to understand the work`));
        cliOutput(chalk.gray(`\nExample: npx claude-flow task orchestrate --task "Design and implement a complete user authentication system with JWT tokens, password hashing, and role-based access control"`));
        process.exit(1);
      }

      if (options.task.trim().length > 1000) {
        spinner.fail(chalk.red(`❌ Task description too long: ${options.task.trim().length} characters`));
        logger.warn('task_description_too_long', { length: options.task.trim().length });
        cliOutput(chalk.yellow(`\n💡 Break complex tasks into smaller, manageable units`));
        process.exit(1);
      }

      spinner.text = 'Connecting to ACGS-2 orchestration engine...';
      logger.info('orchestrate_task_started', { strategy: options.strategy, priority: options.priority, taskLength: options.task.trim().length });

      // Orchestrate the task
      const result = await orchestrateTask({
        task: options.task.trim(),
        strategy: options.strategy,
        priority: options.priority
      });

      if (result.success) {
        spinner.succeed(chalk.green(`✅ Task orchestration initiated successfully!`));
        logger.info('orchestrate_task_completed', { taskId: result.taskId, workflowId: result.workflowId });

        cliOutput(chalk.blue(`\n📋 Task Details:`));
        cliOutput(chalk.gray(`   Task ID: ${result.taskId}`));
        cliOutput(chalk.gray(`   Workflow ID: ${result.workflowId}`));
        cliOutput(chalk.gray(`   Strategy: ${options.strategy}`));
        cliOutput(chalk.gray(`   Priority: ${options.priority}`));
        cliOutput(chalk.gray(`   Description: ${options.task}`));

        cliOutput(chalk.green(`\n🚀 Task submitted to swarm for orchestration!`));

        // Show strategy-specific information
        switch (options.strategy) {
          case 'sequential':
            cliOutput(chalk.cyan(`\n🔄 Sequential Strategy: Tasks will be executed one after another`));
            break;
          case 'parallel':
            cliOutput(chalk.cyan(`\n🔄 Parallel Strategy: Tasks will be executed simultaneously`));
            break;
          case 'hierarchical':
            cliOutput(chalk.cyan(`\n🔄 Hierarchical Strategy: Coordinator will oversee specialized agents`));
            break;
          case 'consensus':
            cliOutput(chalk.cyan(`\n🔄 Consensus Strategy: Multiple agents will collaborate and vote`));
            break;
        }

      } else {
        spinner.fail(chalk.red(`❌ Failed to orchestrate task`));
        logger.error('orchestrate_task_failed', { error: result.error });
        cliOutput(chalk.red(`\nError: ${result.error}`));
        cliOutput(chalk.yellow(`\n💡 Make sure the ACGS-2 system is running and accessible`));
        process.exit(1);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      spinner.fail(chalk.red(`❌ Error orchestrating task: ${errorMessage}`));
      logger.error('orchestrate_task_exception', { error: errorMessage });

      // Provide helpful error context
      if (errorMessage.includes('python3')) {
        cliOutput(chalk.yellow(`\n💡 Make sure Python 3 is installed and available in PATH`));
      } else if (errorMessage.includes('EnhancedAgentBus')) {
        cliOutput(chalk.yellow(`\n💡 Make sure the ACGS-2 core is properly installed`));
      }

      process.exit(1);
    }
  });

taskCommand.addCommand(orchestrateCommand);
