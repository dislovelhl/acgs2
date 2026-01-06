/**
 * Agent Command Module
 *
 * This module provides CLI commands for managing individual agents in ACGS-2 swarms, including:
 * - Spawning new agents with specific types and skills
 * - Listing active agents with filtering capabilities
 * - Managing agent lifecycle and configurations
 *
 * @module agent
 */

import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import { spawnAgent, listAgents } from '../services/agentService';
import { getLogger } from '../../../sdk/typescript/src/utils/logger';
const logger = getLogger('agent');

/**
 * Main agent command that provides subcommands for agent management.
 * Use this command to spawn, list, and manage individual agents in the swarm.
 *
 * Available subcommands:
 * - spawn: Create and spawn a new agent with specified type and skills
 * - list: Display all active agents with optional filtering
 *
 * @example
 * ```bash
 * # Spawn a coder agent with custom name
 * npx claude-flow agent spawn --type coder --name my-coder
 *
 * # Spawn a researcher with specific skills
 * npx claude-flow agent spawn --type researcher --skills "ml,nlp,data-analysis"
 *
 * # List all active agents
 * npx claude-flow agent list --verbose
 *
 * # Filter agents by type
 * npx claude-flow agent list --type coder
 * ```
 */
export const agentCommand = new Command('agent')
  .description('Manage agents in the swarm');

// Valid agent types
const VALID_AGENT_TYPES = ['coder', 'researcher', 'analyst', 'tester', 'coordinator'] as const;

/**
 * Valid agent type classifications.
 *
 * - coder: Software development and code implementation (👨‍💻)
 * - researcher: Information gathering and research tasks (🔬)
 * - analyst: Data analysis and insights generation (📊)
 * - tester: Quality assurance and testing (🧪)
 * - coordinator: Task coordination and orchestration (🎯)
 */
type AgentType = typeof VALID_AGENT_TYPES[number];

/**
 * Validates if a string is a valid agent type.
 *
 * @param type - The agent type string to validate
 * @returns True if the type is valid (coder, researcher, analyst, tester, or coordinator)
 *
 * @example
 * ```typescript
 * if (validateAgentType('coder')) {
 *   console.log('Valid agent type');
 * }
 * ```
 */
function validateAgentType(type: string): type is AgentType {
  return VALID_AGENT_TYPES.includes(type as AgentType);
}

/**
 * Validates and parses a comma-separated skills string into a normalized array.
 * Trims whitespace, removes empty entries, and converts to lowercase.
 *
 * @param skills - Comma-separated skills string
 * @returns Array of normalized skill strings, or empty array if input is empty
 *
 * @example
 * ```typescript
 * const skills = validateSkills('Python, JavaScript, Machine Learning');
 * // Returns: ['python', 'javascript', 'machine learning']
 *
 * const empty = validateSkills('');
 * // Returns: []
 * ```
 */
function validateSkills(skills: string): string[] {
  if (!skills || skills.trim() === '') {
    return [];
  }

  return skills.split(',')
    .map(skill => skill.trim())
    .filter(skill => skill.length > 0)
    .map(skill => skill.toLowerCase());
}

/**
 * Returns the emoji icon associated with a given agent type.
 *
 * @param type - The agent type
 * @returns The emoji string for the agent type, or default robot emoji if unknown
 *
 * @example
 * ```typescript
 * const emoji = getAgentEmoji('coder');
 * // Returns: '👨‍💻'
 *
 * const fallback = getAgentEmoji('unknown');
 * // Returns: '🤖'
 * ```
 */
function getAgentEmoji(type: string): string {
  const emojiMap: Record<string, string> = {
    coder: '👨‍💻',
    researcher: '🔬',
    analyst: '📊',
    tester: '🧪',
    coordinator: '🎯'
  };
  return emojiMap[type] || '🤖';
}

/**
 * Generates a unique agent name based on type and timestamp, or returns the custom name if provided.
 * Auto-generated names use the format: `{type}-{timestamp}-{random}`.
 *
 * @param type - The agent type
 * @param customName - Optional custom name provided by user
 * @returns The agent name (custom if provided, otherwise auto-generated)
 *
 * @example
 * ```typescript
 * const custom = generateAgentName('coder', 'my-special-coder');
 * // Returns: 'my-special-coder'
 *
 * const auto = generateAgentName('coder');
 * // Returns: 'coder-lx4h2k-9f3k1' (example)
 * ```
 */
function generateAgentName(type: AgentType, customName?: string): string {
  if (customName && customName.trim()) {
    return customName.trim();
  }

  // Generate a unique name based on type and timestamp
  const timestamp = Date.now().toString(36);
  const random = Math.random().toString(36).substr(2, 5);
  return `${type}-${timestamp}-${random}`;
}

const spawnCommand = new Command('spawn')
  .description('Spawn a new agent in the current swarm')
  .requiredOption('-t, --type <type>', `Agent type (${VALID_AGENT_TYPES.join(', ')})`, 'coder')
  .option('-n, --name <name>', 'Custom agent name')
  .option('-s, --skills <skills>', 'Specific skills (comma-separated)')
  .action(async (options) => {
    try {
      const spinner = ora('Validating options...').start();

        logger.info(chalk.yellow(`\n📋 Valid types: ${VALID_AGENT_TYPES.join(', ')}`));
        logger.info(chalk.gray(`\nExample: npx claude-flow agent spawn --type coder`));
      if (!validateAgentType(options.type)) {
        spinner.fail(chalk.red(`❌ Invalid agent type: ${options.type}`));
        logger.warn('invalid_agent_type', { type: options.type });
        cliOutput(chalk.yellow(`\n📋 Valid types: ${VALID_AGENT_TYPES.join(', ')}`));
        cliOutput(chalk.gray(`\nExample: npx claude-flow agent spawn --type coder`));
        process.exit(1);
      }

      // Validate and parse skills
      const skills = validateSkills(options.skills || '');

      // Generate or validate agent name
      const agentName = generateAgentName(options.type, options.name);
        logger.info(chalk.yellow(`\n💡 Agent names must be at least 3 characters long`));
      // Validate agent name
      if (agentName.length < 3) {
        spinner.fail(chalk.red(`❌ Agent name too short: ${agentName}`));
        logger.warn('agent_name_too_short', { name: agentName });
        cliOutput(chalk.yellow(`\n💡 Agent names must be at least 3 characters long`));
        process.exit(1);
        logger.info(chalk.yellow(`\n💡 Agent names must be less than 50 characters`));

      if (agentName.length > 50) {
        spinner.fail(chalk.red(`❌ Agent name too long: ${agentName}`));
        logger.warn('agent_name_too_long', { name: agentName });
        cliOutput(chalk.yellow(`\n💡 Agent names must be less than 50 characters`));
        process.exit(1);
      }
        logger.info(chalk.yellow(`\n💡 Agent names can only contain letters, numbers, hyphens, and underscores`));
      // Check for invalid characters in name
      if (!/^[a-zA-Z0-9\-_]+$/.test(agentName)) {
        spinner.fail(chalk.red(`❌ Invalid characters in agent name: ${agentName}`));
        logger.warn('agent_name_invalid_chars', { name: agentName });
        cliOutput(chalk.yellow(`\n💡 Agent names can only contain letters, numbers, hyphens, and underscores`));
        process.exit(1);
      }

      spinner.text = 'Connecting to ACGS-2 bus...';
      logger.info('spawn_agent_started', { type: options.type, name: agentName, skills });

      // Spawn the agent
      const result = await spawnAgent({
        name: agentName,
        type: options.type,
        skills: skills
      });

      if (result.success) {
        logger.info(chalk.blue(`\n🤖 Agent Details:`));
        logger.info(chalk.gray(`   ID: ${result.agentId}`));
        logger.info(chalk.gray(`   Type: ${options.type}`));
        logger.info(chalk.gray(`   Name: ${agentName}`));
        console.log(chalk.blue(`\n🤖 Agent Details:`));
        console.log(chalk.gray(`   ID: ${result.agentId}`));
        console.log(chalk.gray(`   Type: ${options.type}`));
        console.log(chalk.gray(`   Name: ${agentName}`));
        logger.info(chalk.green(`\n🚀 Agent is now active in the swarm!`));
        console.log(chalk.green(`\n🚀 Agent is now active in the swarm!`));
        if (skills.length > 0) {
          logger.info(chalk.gray(`   Skills: ${skills.join(', ')}`));
          console.log(chalk.gray(`   Skills: ${skills.join(', ')}`));
        }
      } else {
        spinner.fail(chalk.red(`❌ Failed to spawn agent`));
        logger.error('spawn_agent_failed', { error: result.error });
        cliOutput(chalk.red(`\nError: ${result.error}`));
        cliOutput(chalk.yellow(`\n💡 Make sure the ACGS-2 system is running and accessible`));
        process.exit(1);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
        logger.info(chalk.yellow(`\n💡 Make sure Python 3 is installed and available in PATH`));

        logger.info(chalk.yellow(`\n💡 Make sure the ACGS-2 core is properly installed`));
      if (errorMessage.includes('python3')) {
        cliOutput(chalk.yellow(`\n💡 Make sure Python 3 is installed and available in PATH`));
      } else if (errorMessage.includes('EnhancedAgentBus')) {
        cliOutput(chalk.yellow(`\n💡 Make sure the ACGS-2 core is properly installed`));
      }

      process.exit(1);
    }
  });

const listCommand = new Command('list')
  .description('List all active agents in the swarm')
  .option('-t, --type <type>', `Filter by agent type (${VALID_AGENT_TYPES.join(', ')})`)
  .option('-v, --verbose', 'Show detailed agent information', false)
  .action(async (options) => {
    const spinner = ora('Retrieving agent list...').start();

        logger.info(chalk.yellow(`\n📋 Valid types: ${VALID_AGENT_TYPES.join(', ')}`));
      // Validate filter type if provided
      if (options.type && !validateAgentType(options.type)) {
        spinner.fail(chalk.red(`❌ Invalid agent type filter: ${options.type}`));
        logger.warn('invalid_agent_type_filter', { type: options.type });
        cliOutput(chalk.yellow(`\n📋 Valid types: ${VALID_AGENT_TYPES.join(', ')}`));
        process.exit(1);
      }

        logger.info(chalk.gray(`\n💡 Spawn agents first: npx claude-flow agent spawn --type coder`));

      if (!agents || agents.length === 0) {
        spinner.warn(chalk.yellow(`⚠️  No active agents found in the swarm`));
        logger.info('no_agents_found');
        cliOutput(chalk.gray(`\n💡 Spawn agents first: npx claude-flow agent spawn --type coder`));
        return;
      }

      // Filter agents by type if specified
      let filteredAgents = agents;
      if (options.type) {
        filteredAgents = agents.filter(agent => agent.type === options.type);
      logger.info(chalk.blue(`\n🤖 Active Agents:`));

      spinner.succeed(chalk.green(`✅ Found ${filteredAgents.length} agent${filteredAgents.length !== 1 ? 's' : ''}`));
      logger.info('agents_found', { count: filteredAgents.length, total: agents.length });

      cliOutput(chalk.blue(`\n🤖 Active Agents:`));

        logger.info(chalk.gray(`${index + 1}. ${agentEmoji} ${agent.name || agent.id} (${agent.type}) ${statusEmoji}`));
        const agentEmoji = getAgentEmoji(agent.type);
        const statusEmoji = agent.status === 'active' ? '🟢' : agent.status === 'busy' ? '🟡' : '🔴';
          logger.info(chalk.gray(`   ID: ${agent.id}`));
          logger.info(chalk.gray(`   Status: ${agent.status}`));

            logger.info(chalk.gray(`   Skills: ${agent.capabilities.join(', ')}`));
          console.log(chalk.gray(`   ID: ${agent.id}`));
          console.log(chalk.gray(`   Status: ${agent.status}`));
          if (agent.capabilities && agent.capabilities.length > 0) {
            logger.info(chalk.gray(`   Created: ${created.toLocaleString()}`));
          }
          if (agent.created_at) {
            const created = new Date(agent.created_at);
            logger.info(chalk.gray(`   Last Active: ${lastActive.toLocaleString()}`));
          }
          if (agent.last_active) {
            const lastActive = new Date(agent.last_active);
            cliOutput(chalk.gray(`   Last Active: ${lastActive.toLocaleString()}`));
          }
          console.log();
        logger.info(chalk.yellow(`\n⚠️  No agents found with type: ${options.type}`));
      });

      logger.info(chalk.blue(`\n📊 Summary:`));
      logger.info(chalk.gray(`   Total Agents: ${agents.length}`));
      }
        logger.info(chalk.gray(`   Filtered by type: ${options.type}`));
      console.log(chalk.blue(`\n📊 Summary:`));
      console.log(chalk.gray(`   Total Agents: ${agents.length}`));
      if (options.type) {
        cliOutput(chalk.gray(`   Filtered by type: ${options.type}`));
      }

      // Show type breakdown
      const typeCounts = agents.reduce((acc, agent) => {
      logger.info(chalk.gray(`   By Type: ${Object.entries(typeCounts).map(([type, count]) => `${type}: ${count}`).join(', ')}`));
        return acc;
      }, {});

      cliOutput(chalk.gray(`   By Type: ${Object.entries(typeCounts).map(([type, count]) => `${type}: ${count}`).join(', ')}`));

    } catch (error) {
        logger.info(chalk.yellow(`\n💡 Make sure Python 3 is installed and available in PATH`));
      spinner.fail(chalk.red(`❌ Failed to list agents: ${errorMessage}`));
        logger.info(chalk.yellow(`\n💡 Make sure the ACGS-2 core is properly installed`));
      if (errorMessage.includes('python3')) {
        cliOutput(chalk.yellow(`\n💡 Make sure Python 3 is installed and available in PATH`));
      } else if (errorMessage.includes('EnhancedAgentBus')) {
        cliOutput(chalk.yellow(`\n💡 Make sure the ACGS-2 core is properly installed`));
      }
    }
  });

agentCommand.addCommand(spawnCommand);
agentCommand.addCommand(listCommand);
