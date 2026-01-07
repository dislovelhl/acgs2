# Add JSDoc coverage for claude-flow TypeScript service public exports

## Overview

The claude-flow TypeScript CLI tool has 45 exported functions/classes across 17 files but only 97 JSDoc comments across 12 files. Key files like src/commands/swarm.ts, src/commands/agent.ts, src/commands/task.ts, and src/services/agentService.ts lack comprehensive JSDoc documentation for their public APIs.

## Rationale

Claude-flow is the primary CLI interface for managing ACGS-2 agent swarms. Enterprise users relying on this tool need comprehensive API documentation for integration and automation. The command files and service layer are particularly critical as they define the user-facing interface.

---
*This spec was created from ideation and is pending detailed specification.*
