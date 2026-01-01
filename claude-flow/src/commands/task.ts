import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import { orchestrateTask } from '../services/taskService';

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
        console.log(chalk.yellow(`\n📋 Valid strategies: ${VALID_STRATEGIES.join(', ')}`));
        console.log(chalk.gray(`\n  sequential: Tasks executed one after another`));
        console.log(chalk.gray(`  parallel: Tasks executed simultaneously`));
        console.log(chalk.gray(`  hierarchical: Coordinator oversees specialized agents`));
        console.log(chalk.gray(`  consensus: Multiple agents vote on approach`));
        console.log(chalk.gray(`\nExample: npx claude-flow task orchestrate --task "Implement authentication" --strategy parallel`));
        process.exit(1);
      }

      // Validate priority
      if (!validatePriority(options.priority)) {
        spinner.fail(chalk.red(`❌ Invalid priority level: ${options.priority}`));
        console.log(chalk.yellow(`\n📋 Valid priorities: ${VALID_PRIORITIES.join(', ')}`));
        console.log(chalk.gray(`\n  low: Standard processing time`));
        console.log(chalk.gray(`  medium: Moderate priority (default)`));
        console.log(chalk.gray(`  high: Expedited processing`));
        console.log(chalk.gray(`  critical: Immediate attention required`));
        console.log(chalk.gray(`\nExample: npx claude-flow task orchestrate --task "Fix production bug" --priority critical`));
        process.exit(1);
      }

      // Validate task description
      if (!options.task || options.task.trim().length === 0) {
        spinner.fail(chalk.red(`❌ Task description cannot be empty`));
        console.log(chalk.yellow(`\n💡 Provide a clear, actionable task description`));
        console.log(chalk.gray(`\nExample: npx claude-flow task orchestrate --task "Implement user authentication system"`));
        process.exit(1);
      }

      if (options.task.trim().length < 10) {
        spinner.fail(chalk.red(`❌ Task description too short: ${options.task.trim().length} characters`));
        console.log(chalk.yellow(`\n💡 Task descriptions should be detailed enough for agents to understand the work`));
        console.log(chalk.gray(`\nExample: npx claude-flow task orchestrate --task "Design and implement a complete user authentication system with JWT tokens, password hashing, and role-based access control"`));
        process.exit(1);
      }

      if (options.task.trim().length > 1000) {
        spinner.fail(chalk.red(`❌ Task description too long: ${options.task.trim().length} characters`));
        console.log(chalk.yellow(`\n💡 Break complex tasks into smaller, manageable units`));
        process.exit(1);
      }

      spinner.text = 'Connecting to ACGS-2 orchestration engine...';

      // Orchestrate the task
      const result = await orchestrateTask({
        task: options.task.trim(),
        strategy: options.strategy,
        priority: options.priority
      });

      if (result.success) {
        spinner.succeed(chalk.green(`✅ Task orchestration initiated successfully!`));

        console.log(chalk.blue(`\n📋 Task Details:`));
        console.log(chalk.gray(`   Task ID: ${result.taskId}`));
        console.log(chalk.gray(`   Workflow ID: ${result.workflowId}`));
        console.log(chalk.gray(`   Strategy: ${options.strategy}`));
        console.log(chalk.gray(`   Priority: ${options.priority}`));
        console.log(chalk.gray(`   Description: ${options.task}`));

        console.log(chalk.green(`\n🚀 Task submitted to swarm for orchestration!`));

        // Show strategy-specific information
        switch (options.strategy) {
          case 'sequential':
            console.log(chalk.cyan(`\n🔄 Sequential Strategy: Tasks will be executed one after another`));
            break;
          case 'parallel':
            console.log(chalk.cyan(`\n🔄 Parallel Strategy: Tasks will be executed simultaneously`));
            break;
          case 'hierarchical':
            console.log(chalk.cyan(`\n🔄 Hierarchical Strategy: Coordinator will oversee specialized agents`));
            break;
          case 'consensus':
            console.log(chalk.cyan(`\n🔄 Consensus Strategy: Multiple agents will collaborate and vote`));
            break;
        }

      } else {
        spinner.fail(chalk.red(`❌ Failed to orchestrate task`));
        console.log(chalk.red(`\nError: ${result.error}`));
        console.log(chalk.yellow(`\n💡 Make sure the ACGS-2 system is running and accessible`));
        process.exit(1);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      spinner.fail(chalk.red(`❌ Error orchestrating task: ${errorMessage}`));

      // Provide helpful error context
      if (errorMessage.includes('python3')) {
        console.log(chalk.yellow(`\n💡 Make sure Python 3 is installed and available in PATH`));
      } else if (errorMessage.includes('EnhancedAgentBus')) {
        console.log(chalk.yellow(`\n💡 Make sure the ACGS-2 core is properly installed`));
      }

      process.exit(1);
    }
  });

taskCommand.addCommand(orchestrateCommand);
