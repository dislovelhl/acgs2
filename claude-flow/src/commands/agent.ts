import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import { spawnAgent, listAgents } from '../services/agentService';

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

    try {
      // Validate agent type
      if (!validateAgentType(options.type)) {
        spinner.fail(chalk.red(`❌ Invalid agent type: ${options.type}`));
        console.log(chalk.yellow(`\n📋 Valid types: ${VALID_AGENT_TYPES.join(', ')}`));
        console.log(chalk.gray(`\nExample: npx claude-flow agent spawn --type coder`));
        process.exit(1);
      }

      // Validate and parse skills
      const skills = validateSkills(options.skills || '');

      // Generate or validate agent name
      const agentName = generateAgentName(options.type, options.name);

      // Validate agent name
      if (agentName.length < 3) {
        spinner.fail(chalk.red(`❌ Agent name too short: ${agentName}`));
        console.log(chalk.yellow(`\n💡 Agent names must be at least 3 characters long`));
        process.exit(1);
      }

      if (agentName.length > 50) {
        spinner.fail(chalk.red(`❌ Agent name too long: ${agentName}`));
        console.log(chalk.yellow(`\n💡 Agent names must be less than 50 characters`));
        process.exit(1);
      }

      // Check for invalid characters in name
      if (!/^[a-zA-Z0-9\-_]+$/.test(agentName)) {
        spinner.fail(chalk.red(`❌ Invalid characters in agent name: ${agentName}`));
        console.log(chalk.yellow(`\n💡 Agent names can only contain letters, numbers, hyphens, and underscores`));
        process.exit(1);
      }

      spinner.text = 'Connecting to ACGS-2 bus...';

      // Spawn the agent
      const result = await spawnAgent({
        name: agentName,
        type: options.type,
        skills: skills
      });

      if (result.success) {
        spinner.succeed(chalk.green(`✅ Agent spawned successfully!`));

        console.log(chalk.blue(`\n🤖 Agent Details:`));
        console.log(chalk.gray(`   ID: ${result.agentId}`));
        console.log(chalk.gray(`   Type: ${options.type}`));
        console.log(chalk.gray(`   Name: ${agentName}`));
        if (skills.length > 0) {
          console.log(chalk.gray(`   Skills: ${skills.join(', ')}`));
        }

        console.log(chalk.green(`\n🚀 Agent is now active in the swarm!`));
      } else {
        spinner.fail(chalk.red(`❌ Failed to spawn agent`));
        console.log(chalk.red(`\nError: ${result.error}`));
        console.log(chalk.yellow(`\n💡 Make sure the ACGS-2 system is running and accessible`));
        process.exit(1);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      spinner.fail(chalk.red(`❌ Error spawning agent: ${errorMessage}`));

      // Provide helpful error context
      if (errorMessage.includes('python3')) {
        console.log(chalk.yellow(`\n💡 Make sure Python 3 is installed and available in PATH`));
      } else if (errorMessage.includes('EnhancedAgentBus')) {
        console.log(chalk.yellow(`\n💡 Make sure the ACGS-2 core is properly installed`));
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

    try {
      // Validate filter type if provided
      if (options.type && !validateAgentType(options.type)) {
        spinner.fail(chalk.red(`❌ Invalid agent type filter: ${options.type}`));
        console.log(chalk.yellow(`\n📋 Valid types: ${VALID_AGENT_TYPES.join(', ')}`));
        process.exit(1);
      }

      const agents = await listAgents();

      if (!agents || agents.length === 0) {
        spinner.warn(chalk.yellow(`⚠️  No active agents found in the swarm`));
        console.log(chalk.gray(`\n💡 Spawn agents first: npx claude-flow agent spawn --type coder`));
        return;
      }

      // Filter agents by type if specified
      let filteredAgents = agents;
      if (options.type) {
        filteredAgents = agents.filter(agent => agent.type === options.type);
      }

      spinner.succeed(chalk.green(`✅ Found ${filteredAgents.length} agent${filteredAgents.length !== 1 ? 's' : ''}`));

      console.log(chalk.blue(`\n🤖 Active Agents:`));

      filteredAgents.forEach((agent, index) => {
        const agentEmoji = getAgentEmoji(agent.type);
        const statusEmoji = agent.status === 'active' ? '🟢' : agent.status === 'busy' ? '🟡' : '🔴';

        console.log(chalk.gray(`${index + 1}. ${agentEmoji} ${agent.name || agent.id} (${agent.type}) ${statusEmoji}`));

        if (options.verbose) {
          console.log(chalk.gray(`   ID: ${agent.id}`));
          console.log(chalk.gray(`   Status: ${agent.status}`));
          if (agent.capabilities && agent.capabilities.length > 0) {
            console.log(chalk.gray(`   Skills: ${agent.capabilities.join(', ')}`));
          }
          if (agent.created_at) {
            const created = new Date(agent.created_at);
            console.log(chalk.gray(`   Created: ${created.toLocaleString()}`));
          }
          if (agent.last_active) {
            const lastActive = new Date(agent.last_active);
            console.log(chalk.gray(`   Last Active: ${lastActive.toLocaleString()}`));
          }
          console.log();
        }
      });

      if (options.type && filteredAgents.length === 0) {
        console.log(chalk.yellow(`\n⚠️  No agents found with type: ${options.type}`));
      }

      console.log(chalk.blue(`\n📊 Summary:`));
      console.log(chalk.gray(`   Total Agents: ${agents.length}`));
      if (options.type) {
        console.log(chalk.gray(`   Filtered by type: ${options.type}`));
      }

      // Show type breakdown
      const typeCounts = agents.reduce((acc, agent) => {
        acc[agent.type] = (acc[agent.type] || 0) + 1;
        return acc;
      }, {});

      console.log(chalk.gray(`   By Type: ${Object.entries(typeCounts).map(([type, count]) => `${type}: ${count}`).join(', ')}`));

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      spinner.fail(chalk.red(`❌ Failed to list agents: ${errorMessage}`));

      if (errorMessage.includes('python3')) {
        console.log(chalk.yellow(`\n💡 Make sure Python 3 is installed and available in PATH`));
      } else if (errorMessage.includes('EnhancedAgentBus')) {
        console.log(chalk.yellow(`\n💡 Make sure the ACGS-2 core is properly installed`));
      }
    }
  });

agentCommand.addCommand(spawnCommand);
agentCommand.addCommand(listCommand);
