import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import { listCoordinationTasks, executeCoordinationTask, getCoordinationStatus, generateCoordinationReport } from '../services/coordinationService';
import { getLogger } from '../../../../../sdk/typescript/src/utils/logger';
const logger = getLogger('coordination');



export const coordinationCommand = new Command('coordination')
  .description('Manage ACGS-2 coordination tasks and actionable recommendations');

// Valid priorities and statuses
const VALID_PRIORITIES = ['critical', 'high', 'medium', 'low'] as const;
const VALID_STATUSES = ['pending', 'in-progress', 'completed', 'failed'] as const;
const VALID_AGENT_TYPES = ['coder', 'analyst', 'security', 'architect', 'researcher'] as const;
const VALID_FORMATS = ['text', 'json', 'markdown'] as const;

type Priority = typeof VALID_PRIORITIES[number];
type Status = typeof VALID_STATUSES[number];
type AgentType = typeof VALID_AGENT_TYPES[number];
type OutputFormat = typeof VALID_FORMATS[number];

function validatePriority(priority: string): priority is Priority {
  return VALID_PRIORITIES.includes(priority as Priority);
}

function validateStatus(status: string): status is Status {
  return VALID_STATUSES.includes(status as Status);
}

function validateAgentType(agentType: string): agentType is AgentType {
  return VALID_AGENT_TYPES.includes(agentType as AgentType);
}

function validateFormat(format: string): format is OutputFormat {
  return VALID_FORMATS.includes(format as OutputFormat);
}

const listCommand = new Command('list')
  .description('List all available coordination tasks by priority')
  .option('-p, --priority <level>', `Filter by priority (${VALID_PRIORITIES.join(', ')})`)
  .option('-a, --agent-type <type>', `Filter by agent type (${VALID_AGENT_TYPES.join(', ')})`)
  .option('-s, --status <status>', `Filter by status (${VALID_STATUSES.join(', ')})`)
  .action(async (options) => {
    const spinner = ora('Retrieving coordination tasks...').start();

        logger.info(chalk.yellow(`\n📋 Valid priorities: ${VALID_PRIORITIES.join(', ')}`);
      // Validate filters if provided
      if (options.priority && !validatePriority(options.priority)) {
        spinner.fail(chalk.red(`❌ Invalid priority filter: ${options.priority}`));
        console.log(chalk.yellow(`\n📋 Valid priorities: ${VALID_PRIORITIES.join(', ')}`));
        process.exit(1);
        logger.info(chalk.yellow(`\n📋 Valid agent types: ${VALID_AGENT_TYPES.join(', ')}`);

      if (options.agentType && !validateAgentType(options.agentType)) {
        spinner.fail(chalk.red(`❌ Invalid agent type filter: ${options.agentType}`));
        console.log(chalk.yellow(`\n📋 Valid agent types: ${VALID_AGENT_TYPES.join(', ')}`));
        process.exit(1);
        logger.info(chalk.yellow(`\n📋 Valid statuses: ${VALID_STATUSES.join(', ')}`);

      if (options.status && !validateStatus(options.status)) {
        spinner.fail(chalk.red(`❌ Invalid status filter: ${options.status}`));
        console.log(chalk.yellow(`\n📋 Valid statuses: ${VALID_STATUSES.join(', ')}`));
        process.exit(1);
      }

      const tasks = await listCoordinationTasks({
        priority: options.priority,
        agentType: options.agentType,
        status: options.status
      });

      if (!tasks || tasks.length === 0) {
        spinner.warn(chalk.yellow(`⚠️  No coordination tasks found matching criteria`));
        return;
      }

      spinner.succeed(chalk.green(`✅ Found ${tasks.length} coordination task${tasks.length !== 1 ? 's' : ''}`));

      // Group tasks by priority
      const criticalTasks = tasks.filter(t => t.priority === 'critical');
      const highTasks = tasks.filter(t => t.priority === 'high');
      const mediumTasks = tasks.filter(t => t.priority === 'medium');
      const lowTasks = tasks.filter(t => t.priority === 'low');

      // Display tasks by priority
      displayTasksByPriority('CRITICAL', criticalTasks, '🚨');
      displayTasksByPriority('HIGH', highTasks, '⚠️');
      logger.info(chalk.blue(`\n📊 Summary:`);
      logger.info(chalk.gray(`   Total Tasks: ${tasks.length}`);
      logger.info(chalk.gray(`   Critical: ${criticalTasks.length}`);
      logger.info(chalk.gray(`   High: ${highTasks.length}`);
      logger.info(chalk.gray(`   Medium: ${mediumTasks.length}`);
      logger.info(chalk.gray(`   Low: ${lowTasks.length}`);
      console.log(chalk.gray(`   Critical: ${criticalTasks.length}`));
      console.log(chalk.gray(`   High: ${highTasks.length}`));
      console.log(chalk.gray(`   Medium: ${mediumTasks.length}`));
      console.log(chalk.gray(`   Low: ${lowTasks.length}`));

    } catch (error) {
        logger.info(chalk.yellow(`\n💡 Make sure Python 3 is installed and available in PATH`);
      spinner.fail(chalk.red(`❌ Failed to list coordination tasks: ${errorMessage}`));
        logger.info(chalk.yellow(`\n💡 Make sure the ACGS-2 core is properly installed`);
      if (errorMessage.includes('python3')) {
        console.log(chalk.yellow(`\n💡 Make sure Python 3 is installed and available in PATH`));
      } else if (errorMessage.includes('ACGS-2')) {
        console.log(chalk.yellow(`\n💡 Make sure the ACGS-2 core is properly installed`));
      }
    }
  });

function displayTasksByPriority(title: string, tasks: any[], emoji: string) {
  if (tasks.length === 0) return;

  const priorityColors = {
    'CRITICAL': chalk.red,
    'HIGH': chalk.yellow,
  logger.info(chalk.blue(`\n${emoji} ${title} PRIORITY TASKS:`);
    'LOW': chalk.gray
  };

  console.log(chalk.blue(`\n${emoji} ${title} PRIORITY TASKS:`));

    logger.info(color(`${index + 1}. ${task.id}: ${task.task}`);
    logger.info(chalk.gray(`   Agent: ${task.agent_type} (${task.skills.join(', ')})`);
    logger.info(chalk.gray(`   Effort: ${task.estimated_effort}`);
    logger.info(chalk.gray(`   Impact: ${task.impact}`);
    logger.info(chalk.gray(`   Status: ${statusEmoji} ${task.status}`);
    logger.info(chalk.gray(`   → ${task.description}`);
    console.log(chalk.gray(`   Effort: ${task.estimated_effort}`));
    console.log(chalk.gray(`   Impact: ${task.impact}`));
    console.log(chalk.gray(`   Status: ${statusEmoji} ${task.status}`));
    console.log(chalk.gray(`   → ${task.description}`));
    console.log();
  });
}

function getStatusEmoji(status: string): string {
  const emojiMap: Record<string, string> = {
    'pending': '⏳',
    'in-progress': '🔄',
    'completed': '✅',
    'failed': '❌'
  };
  return emojiMap[status] || '❓';
}

const executeCommand = new Command('execute')
  .description('Execute a specific coordination task')
  .argument('<task-id>', 'Task ID to execute')
  .option('--dry-run', 'Show what would be executed without running', false)
  .option('--force', 'Force execution even if prerequisites not met', false)
  .option('--parallel', 'Execute in parallel with other tasks (if supported)', false)
  .action(async (taskId, options) => {
    const spinner = ora(`${options.dryRun ? 'Analyzing' : 'Executing'} coordination task ${taskId}...`).start();

    try {
      const result = await executeCoordinationTask({
        taskId,
        dryRun: options.dryRun,
        force: options.force,
        parallel: options.parallel
      });

      if (result.success) {
        if (options.dryRun) {
          spinner.succeed(chalk.green(`✅ Dry run completed for task ${taskId}`));
        logger.info(chalk.blue(`\n📋 Execution Details:`);
        logger.info(chalk.gray(`   Task ID: ${result.taskId}`);
        logger.info(chalk.gray(`   Status: ${result.status}`);

          logger.info(chalk.gray(`   Execution Time: ${result.executionTime}`);
        console.log(chalk.gray(`   Task ID: ${result.taskId}`));
        console.log(chalk.gray(`   Status: ${result.status}`));
          logger.info(chalk.gray(`   Agent Assigned: ${result.agentAssigned}`);
          console.log(chalk.gray(`   Execution Time: ${result.executionTime}`));
        }
        if (result.agentAssigned) {
          logger.info(chalk.yellow(`\n🔍 Dry Run Results:`);
          logger.info(chalk.gray(`   ${result.details || 'No additional details available'}`);

          logger.info(chalk.green(`\n🚀 Task completed successfully!`);
          console.log(chalk.yellow(`\n🔍 Dry Run Results:`));
          console.log(chalk.gray(`   ${result.details || 'No additional details available'}`));
        } else {
          console.log(chalk.green(`\n🚀 Task completed successfully!`));
        logger.info(chalk.red(`\nError: ${result.error}`);

      } else {
          logger.info(chalk.yellow(`\n💡 Details: ${result.details}`);
        console.log(chalk.red(`\nError: ${result.error}`));

        if (result.details) {
          console.log(chalk.yellow(`\n💡 Details: ${result.details}`));
        }

        process.exit(1);
      }
    } catch (error) {
        logger.info(chalk.yellow(`\n💡 Make sure Python 3 is installed and available in PATH`);
      spinner.fail(chalk.red(`❌ Error executing coordination task: ${errorMessage}`));
        logger.info(chalk.yellow(`\n💡 Make sure the ACGS-2 core is properly installed`);
      if (errorMessage.includes('python3')) {
        console.log(chalk.yellow(`\n💡 Make sure Python 3 is installed and available in PATH`));
      } else if (errorMessage.includes('ACGS-2')) {
        console.log(chalk.yellow(`\n💡 Make sure the ACGS-2 core is properly installed`));
      }

      process.exit(1);
    }
  });

const statusCommand = new Command('status')
  .description('Check the status of coordination tasks')
  .option('--task-id <id>', 'Check specific task status')
  .option('-v, --verbose', 'Show detailed status information', false)
  .option('--progress', 'Show progress indicators', false)
  .action(async (options) => {
    const spinner = ora('Checking coordination status...').start();

    try {
      const status = await getCoordinationStatus({
        taskId: options.taskId,
        verbose: options.verbose,
        progress: options.progress
      });

      if (!status || (Array.isArray(status) && status.length === 0)) {
        spinner.warn(chalk.yellow(`⚠️  No coordination tasks found`));
        return;
      }

      spinner.succeed(chalk.green(`✅ Coordination status retrieved`));

      if (Array.isArray(status)) {
        // Multiple tasks status
        displayMultipleTasksStatus(status, options.verbose, options.progress);
      } else {
        // Single task status
        displaySingleTaskStatus(status, options.verbose);
      }

    } catch (error) {
        logger.info(chalk.yellow(`\n💡 Make sure Python 3 is installed and available in PATH`);
      spinner.fail(chalk.red(`❌ Failed to get coordination status: ${errorMessage}`));
        logger.info(chalk.yellow(`\n💡 Make sure the ACGS-2 core is properly installed`);
      if (errorMessage.includes('python3')) {
        console.log(chalk.yellow(`\n💡 Make sure Python 3 is installed and available in PATH`));
      } else if (errorMessage.includes('ACGS-2')) {
        console.log(chalk.yellow(`\n💡 Make sure the ACGS-2 core is properly installed`));
      }
  logger.info(chalk.blue(`\n📊 Coordination Tasks Status:`);
  });

function displayMultipleTasksStatus(tasks: any[], verbose: boolean, showProgress: boolean) {
  console.log(chalk.blue(`\n📊 Coordination Tasks Status:`));

  const statusCounts = tasks.reduce((acc, task) => {
  logger.info(chalk.gray(`\n📈 Overview:`);
  logger.info(chalk.gray(`   Total Tasks: ${tasks.length}`);
  }, {});

    logger.info(chalk.gray(`   ${emoji} ${status}: ${count}`);
  console.log(chalk.gray(`   Total Tasks: ${tasks.length}`));
  Object.entries(statusCounts).forEach(([status, count]) => {
    const emoji = getStatusEmoji(status);
    console.log(chalk.gray(`   ${emoji} ${status}: ${count}`));
  });
    logger.info(chalk.gray(`   📊 Progress: ${progress}% (${completed}/${tasks.length} completed)`);
  if (showProgress) {
    const completed = statusCounts.completed || 0;
    const progress = Math.round((completed / tasks.length) * 100);
    logger.info(chalk.blue(`\n📋 Detailed Status:`);
  }

  if (verbose) {
    console.log(chalk.blue(`\n📋 Detailed Status:`));
      logger.info(color(`${index + 1}. ${task.id}: ${statusEmoji} ${task.status}`);
      const statusEmoji = getStatusEmoji(task.status);
        logger.info(chalk.gray(`   Last Updated: ${new Date(task.lastUpdated).toLocaleString()}`);

      console.log(color(`${index + 1}. ${task.id}: ${statusEmoji} ${task.status}`));
        logger.info(chalk.gray(`   Progress: ${task.progress}%`);
        console.log(chalk.gray(`   Last Updated: ${new Date(task.lastUpdated).toLocaleString()}`));
      }
      if (task.progress) {
        console.log(chalk.gray(`   Progress: ${task.progress}%`));
      }
    });
  logger.info(chalk.blue(`\n📋 Task Status:`);
}

function displaySingleTaskStatus(task: any, verbose: boolean) {
  console.log(chalk.blue(`\n📋 Task Status:`));
  logger.info(color(`Task ID: ${task.id}`);
  logger.info(color(`Status: ${statusEmoji} ${task.status}`);
  logger.info(chalk.gray(`Description: ${task.description}`);

  console.log(color(`Task ID: ${task.id}`));
    logger.info(chalk.gray(`Last Updated: ${new Date(task.lastUpdated).toLocaleString()}`);
  console.log(chalk.gray(`Description: ${task.description}`));

  if (task.lastUpdated) {
    console.log(chalk.gray(`Last Updated: ${new Date(task.lastUpdated).toLocaleString()}`));
    logger.info(chalk.gray(`Progress: ${progressBar} ${task.progress}%`);

  if (task.progress !== undefined) {
    const progressBar = createProgressBar(task.progress);
    logger.info(chalk.blue(`\n📊 Detailed Information:`);
  }
      logger.info(chalk.gray(`   ${key}: ${value}`);
  if (verbose && task.details) {
    console.log(chalk.blue(`\n📊 Detailed Information:`));
    Object.entries(task.details).forEach(([key, value]) => {
      console.log(chalk.gray(`   ${key}: ${value}`));
    });
  }
}

function getStatusColor(status: string): (text: string) => string {
  const colorMap: Record<string, (text: string) => string> = {
    'pending': chalk.gray,
    'in-progress': chalk.yellow,
    'completed': chalk.green,
    'failed': chalk.red
  };
  return colorMap[status] || chalk.gray;
}

function createProgressBar(progress: number): string {
  const width = 20;
  const filled = Math.round((progress / 100) * width);
  const empty = width - filled;
  return '█'.repeat(filled) + '░'.repeat(empty);
}

const reportCommand = new Command('report')
  .description('Generate a coordination progress report')
  .option('-f, --format <type>', `Output format (${VALID_FORMATS.join(', ')})`, 'text')
  .option('-p, --period <days>', 'Report period in days', '30')
  .option('--include-completed', 'Include completed tasks in report', false)
  .action(async (options) => {
    const spinner = ora('Generating coordination report...').start();

        logger.info(chalk.yellow(`\n📋 Valid formats: ${VALID_FORMATS.join(', ')}`);
      // Validate format
      if (!validateFormat(options.format)) {
        spinner.fail(chalk.red(`❌ Invalid format: ${options.format}`));
        console.log(chalk.yellow(`\n📋 Valid formats: ${VALID_FORMATS.join(', ')}`));
        process.exit(1);
      }

      // Validate period
      const period = parseInt(options.period, 10);
      if (isNaN(period) || period < 1) {
        spinner.fail(chalk.red(`❌ Invalid period: ${options.period}. Must be a positive number.`));
        process.exit(1);
      }

      const report = await generateCoordinationReport({
        format: options.format,
        period,
        includeCompleted: options.includeCompleted
      });
        logger.info(JSON.stringify(report, null, 2);
      spinner.succeed(chalk.green(`✅ Coordination report generated`));
        logger.info(generateMarkdownReport(report);
      if (options.format === 'json') {
        logger.info(generateTextReport(report);
      } else if (options.format === 'markdown') {
        console.log(generateMarkdownReport(report));
      } else {
        console.log(generateTextReport(report));
      }

    } catch (error) {
        logger.info(chalk.yellow(`\n💡 Make sure Python 3 is installed and available in PATH`);
      spinner.fail(chalk.red(`❌ Failed to generate coordination report: ${errorMessage}`));
        logger.info(chalk.yellow(`\n💡 Make sure the ACGS-2 core is properly installed`);
      if (errorMessage.includes('python3')) {
        console.log(chalk.yellow(`\n💡 Make sure Python 3 is installed and available in PATH`));
      } else if (errorMessage.includes('ACGS-2')) {
        console.log(chalk.yellow(`\n💡 Make sure the ACGS-2 core is properly installed`));
      }
    }
  });

function generateTextReport(report: any): string {
  let output = '';

  output += `ACGS-2 Coordination Report\n`;
  output += `Generated: ${new Date().toISOString()}\n`;
  output += `Period: ${report.period} days\n`;
  output += `=\n\n`;

  output += `EXECUTIVE SUMMARY\n`;
  output += `Total Tasks: ${report.summary.totalTasks}\n`;
  output += `Completed: ${report.summary.completed}\n`;
  output += `In Progress: ${report.summary.inProgress}\n`;
  output += `Pending: ${report.summary.pending}\n`;
  output += `Failed: ${report.summary.failed}\n`;
  output += `Overall Progress: ${report.summary.overallProgress}%\n\n`;

  if (report.tasks && report.tasks.length > 0) {
    output += `TASK DETAILS\n`;
    report.tasks.forEach((task: any) => {
      output += `${task.id}: ${task.task}\n`;
      output += `  Status: ${task.status}\n`;
      output += `  Priority: ${task.priority}\n`;
      output += `  Agent: ${task.agent_type}\n`;
      if (task.progress !== undefined) {
        output += `  Progress: ${task.progress}%\n`;
      }
      output += `\n`;
    });
  }

  return output;
}

function generateMarkdownReport(report: any): string {
  let output = '';

  output += `# ACGS-2 Coordination Report\n\n`;
  output += `**Generated:** ${new Date().toISOString()}\n`;
  output += `**Period:** ${report.period} days\n\n`;

  output += `## Executive Summary\n\n`;
  output += `- **Total Tasks:** ${report.summary.totalTasks}\n`;
  output += `- **Completed:** ${report.summary.completed}\n`;
  output += `- **In Progress:** ${report.summary.inProgress}\n`;
  output += `- **Pending:** ${report.summary.pending}\n`;
  output += `- **Failed:** ${report.summary.failed}\n`;
  output += `- **Overall Progress:** ${report.summary.overallProgress}%\n\n`;

  if (report.tasks && report.tasks.length > 0) {
    output += `## Task Details\n\n`;

    const priorityOrder = ['critical', 'high', 'medium', 'low'];
    priorityOrder.forEach(priority => {
      const priorityTasks = report.tasks.filter((t: any) => t.priority === priority);
      if (priorityTasks.length > 0) {
        output += `### ${priority.charAt(0).toUpperCase() + priority.slice(1)} Priority\n\n`;
        priorityTasks.forEach((task: any) => {
          const statusEmoji = getStatusEmoji(task.status);
          output += `#### ${task.id}: ${task.task}\n\n`;
          output += `- **Status:** ${statusEmoji} ${task.status}\n`;
          output += `- **Agent:** ${task.agent_type}\n`;
          output += `- **Skills:** ${task.skills.join(', ')}\n`;
          output += `- **Effort:** ${task.estimated_effort}\n`;
          output += `- **Impact:** ${task.impact}\n`;
          if (task.progress !== undefined) {
            output += `- **Progress:** ${task.progress}%\n`;
          }
          output += `- **Description:** ${task.description}\n\n`;
        });
      }
    });
  }

  return output;
}

coordinationCommand.addCommand(listCommand);
coordinationCommand.addCommand(executeCommand);
coordinationCommand.addCommand(statusCommand);
coordinationCommand.addCommand(reportCommand);
