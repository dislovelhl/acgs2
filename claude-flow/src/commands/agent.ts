import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import { spawnAgent, listAgents } from '../services/agentService';
import { getLogger, cliOutput } from '../utils/logging_config';

// Initialize logger for this module
const logger = getLogger('commands/agent');

export const agentCommand = new Command('agent')
  .description('Manage agents in the swarm');

// Valid agent types
const VALID_AGENT_TYPES = ['coder', 'researcher', 'analyst', 'tester', 'coordinator'] as const;
type AgentType = typeof VALID_AGENT_TYPES[number];

function validateAgentType(type: string): type is AgentType {
  return VALID_AGENT_TYPES.includes(type as AgentType);
}

function validateSkills(skills: string): string[] {
  if (!skills || skills.trim() === '') {
    return [];
  }

  return skills.split(',')
    .map(skill => skill.trim())
    .filter(skill => skill.length > 0)
    .map(skill => skill.toLowerCase());
}

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
    const spinner = ora('Validating options...').start();

        logger.info(chalk.yellow(`\n📋 Valid types: ${VALID_AGENT_TYPES.join(', ')}`);
        logger.info(chalk.gray(`\nExample: npx claude-flow agent spawn --type coder`);
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
        logger.info(chalk.yellow(`\n💡 Agent names must be at least 3 characters long`);
      // Validate agent name
      if (agentName.length < 3) {
        spinner.fail(chalk.red(`❌ Agent name too short: ${agentName}`));
        logger.warn('agent_name_too_short', { name: agentName });
        cliOutput(chalk.yellow(`\n💡 Agent names must be at least 3 characters long`));
        process.exit(1);
        logger.info(chalk.yellow(`\n💡 Agent names must be less than 50 characters`);

      if (agentName.length > 50) {
        spinner.fail(chalk.red(`❌ Agent name too long: ${agentName}`));
        logger.warn('agent_name_too_long', { name: agentName });
        cliOutput(chalk.yellow(`\n💡 Agent names must be less than 50 characters`));
        process.exit(1);
      }
        logger.info(chalk.yellow(`\n💡 Agent names can only contain letters, numbers, hyphens, and underscores`);
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
        spinner.succeed(chalk.green(`✅ Agent spawned successfully!`));
        logger.info('agent_spawned', { agentId: result.agentId, type: options.type, name: agentName });

        cliOutput(chalk.blue(`\n🤖 Agent Details:`));
        cliOutput(chalk.gray(`   ID: ${result.agentId}`));
        cliOutput(chalk.gray(`   Type: ${options.type}`));
        cliOutput(chalk.gray(`   Name: ${agentName}`));
        if (skills.length > 0) {
          cliOutput(chalk.gray(`   Skills: ${skills.join(', ')}`));
        }

        cliOutput(chalk.green(`\n🚀 Agent is now active in the swarm!`));
      } else {
        spinner.fail(chalk.red(`❌ Failed to spawn agent`));
        logger.error('spawn_agent_failed', { error: result.error });
        cliOutput(chalk.red(`\nError: ${result.error}`));
        cliOutput(chalk.yellow(`\n💡 Make sure the ACGS-2 system is running and accessible`));
        process.exit(1);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      spinner.fail(chalk.red(`❌ Error spawning agent: ${errorMessage}`));
      logger.error('spawn_agent_exception', { error: errorMessage });

        logger.info(chalk.yellow(`\n💡 Make sure the ACGS-2 core is properly installed`);
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

        logger.info(chalk.yellow(`\n📋 Valid types: ${VALID_AGENT_TYPES.join(', ')}`);
      // Validate filter type if provided
      if (options.type && !validateAgentType(options.type)) {
        spinner.fail(chalk.red(`❌ Invalid agent type filter: ${options.type}`));
        logger.warn('invalid_agent_type_filter', { type: options.type });
        cliOutput(chalk.yellow(`\n📋 Valid types: ${VALID_AGENT_TYPES.join(', ')}`));
        process.exit(1);
      }

      logger.info('list_agents_started', { typeFilter: options.type });

      const agents = await listAgents();

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
      logger.info(chalk.blue(`\n🤖 Active Agents:`);

      spinner.succeed(chalk.green(`✅ Found ${filteredAgents.length} agent${filteredAgents.length !== 1 ? 's' : ''}`));
      logger.info('agents_found', { count: filteredAgents.length, total: agents.length });

      cliOutput(chalk.blue(`\n🤖 Active Agents:`));

        logger.info(chalk.gray(`${index + 1}. ${agentEmoji} ${agent.name || agent.id} (${agent.type}) ${statusEmoji}`);
        const agentEmoji = getAgentEmoji(agent.type);
        const statusEmoji = agent.status === 'active' ? '🟢' : agent.status === 'busy' ? '🟡' : '🔴';
          logger.info(chalk.gray(`   ID: ${agent.id}`);
          logger.info(chalk.gray(`   Status: ${agent.status}`);

        cliOutput(chalk.gray(`${index + 1}. ${agentEmoji} ${agent.name || agent.id} (${agent.type}) ${statusEmoji}`));

        if (options.verbose) {
          cliOutput(chalk.gray(`   ID: ${agent.id}`));
          cliOutput(chalk.gray(`   Status: ${agent.status}`));
          if (agent.capabilities && agent.capabilities.length > 0) {
            cliOutput(chalk.gray(`   Skills: ${agent.capabilities.join(', ')}`));
          }
          if (agent.created_at) {
            const created = new Date(agent.created_at);
            cliOutput(chalk.gray(`   Created: ${created.toLocaleString()}`));
          }
          if (agent.last_active) {
            const lastActive = new Date(agent.last_active);
            cliOutput(chalk.gray(`   Last Active: ${lastActive.toLocaleString()}`));
          }
          cliOutput('');
        }
      });

      if (options.type && filteredAgents.length === 0) {
        cliOutput(chalk.yellow(`\n⚠️  No agents found with type: ${options.type}`));
      }

      cliOutput(chalk.blue(`\n📊 Summary:`));
      cliOutput(chalk.gray(`   Total Agents: ${agents.length}`));
      if (options.type) {
        cliOutput(chalk.gray(`   Filtered by type: ${options.type}`));
      }

      // Show type breakdown
      const typeCounts = agents.reduce((acc, agent) => {
      logger.info(chalk.gray(`   By Type: ${Object.entries(typeCounts).map(([type, count]) => `${type}: ${count}`).join(', ')}`);
        return acc;
      }, {});

      cliOutput(chalk.gray(`   By Type: ${Object.entries(typeCounts).map(([type, count]) => `${type}: ${count}`).join(', ')}`));

    } catch (error) {
        logger.info(chalk.yellow(`\n💡 Make sure Python 3 is installed and available in PATH`);
      spinner.fail(chalk.red(`❌ Failed to list agents: ${errorMessage}`));
      logger.error('list_agents_failed', { error: errorMessage });

      if (errorMessage.includes('python3')) {
        cliOutput(chalk.yellow(`\n💡 Make sure Python 3 is installed and available in PATH`));
      } else if (errorMessage.includes('EnhancedAgentBus')) {
        cliOutput(chalk.yellow(`\n💡 Make sure the ACGS-2 core is properly installed`));
      }
    }
  });

agentCommand.addCommand(spawnCommand);
agentCommand.addCommand(listCommand);
