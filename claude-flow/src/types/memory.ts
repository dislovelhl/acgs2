/**
 * Memory Types - TypeScript interfaces for persistent memory operations
 *
 * @module types/memory
 */

/**
 * Configuration for the memory service
 */
export interface MemoryConfig {
  /** Redis connection URL (supports both redis:// and rediss://) */
  redisUrl: string;
  /** Redis password (optional, for production) */
  redisPassword?: string;
  /** Default TTL in seconds for memory entries (default: 24 hours) */
  defaultTtlSeconds: number;
  /** Maximum reconnection attempts before giving up */
  maxReconnectAttempts: number;
  /** Key prefix for all memory entries */
  keyPrefix: string;
}

/**
 * A memory entry stored in Redis
 */
export interface MemoryEntry<T = unknown> {
  /** The stored value */
  value: T;
  /** Timestamp when the entry was created */
  createdAt: string;
  /** Timestamp when the entry was last updated */
  updatedAt: string;
  /** Optional metadata */
  metadata?: Record<string, unknown>;
}

/**
 * Result of a memory operation
 */
export interface MemoryOperationResult {
  /** Whether the operation succeeded */
  success: boolean;
  /** Error message if operation failed */
  error?: string;
}

/**
 * Governance state stored in memory
 */
export interface GovernanceState {
  /** Current governance mode */
  mode: 'active' | 'passive' | 'learning';
  /** Last decision timestamp */
  lastDecision?: string;
  /** Running statistics */
  stats: {
    decisionsProcessed: number;
    approvalsGranted: number;
    denials: number;
    escalations: number;
  };
  /** Cached policy versions */
  policyVersions?: Record<string, string>;
}

/**
 * Agent memory for tracking agent state
 */
export interface AgentMemory {
  /** Agent identifier */
  agentId: string;
  /** Agent type */
  type: string;
  /** Agent skills */
  skills: string[];
  /** Last activity timestamp */
  lastActivity: string;
  /** Number of tasks completed */
  tasksCompleted: number;
  /** Custom agent data */
  data?: Record<string, unknown>;
}

/**
 * Swarm memory for tracking swarm coordination
 */
export interface SwarmMemory {
  /** Swarm identifier */
  swarmId: string;
  /** Swarm status */
  status: 'initializing' | 'active' | 'paused' | 'terminated';
  /** Member agent IDs */
  members: string[];
  /** Coordination strategy */
  strategy: string;
  /** Created timestamp */
  createdAt: string;
  /** Custom swarm data */
  data?: Record<string, unknown>;
}

/**
 * Task memory for tracking task execution
 */
export interface TaskMemory {
  /** Task identifier */
  taskId: string;
  /** Task status */
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled';
  /** Assigned agent ID */
  assignedTo?: string;
  /** Task priority */
  priority: 'low' | 'medium' | 'high' | 'critical';
  /** Created timestamp */
  createdAt: string;
  /** Completed timestamp */
  completedAt?: string;
  /** Task result */
  result?: unknown;
}
