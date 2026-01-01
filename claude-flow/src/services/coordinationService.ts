import { spawn } from 'child_process';
import path from 'path';

export interface CoordinationTaskFilters {
  priority?: string;
  agentType?: string;
  status?: string;
}

export interface CoordinationTaskExecution {
  taskId: string;
  dryRun?: boolean;
  force?: boolean;
  parallel?: boolean;
}

export interface CoordinationStatusOptions {
  taskId?: string;
  verbose?: boolean;
  progress?: boolean;
}

export interface CoordinationReportOptions {
  format: string;
  period: number;
  includeCompleted?: boolean;
}

// Type definitions for coordination tasks
export interface CoordinationTask {
  id: string;
  name?: string;
  priority?: string;
  status?: string;
  agentType?: string;
  createdAt?: string;
  updatedAt?: string;
  metadata?: Record<string, unknown>;
}

export interface TaskExecutionResult {
  success: boolean;
  taskId: string;
  status?: string;
  executionTime?: number;
  agentAssigned?: string;
  details?: Record<string, unknown>;
  error?: string;
}

export interface CoordinationStatus {
  activeTasks?: number;
  completedTasks?: number;
  pendingTasks?: number;
  agentStatuses?: Record<string, string>;
  lastUpdate?: string;
}

export interface CoordinationReport {
  period: number;
  format: string;
  summary?: {
    totalTasks: number;
    completedTasks: number;
    failedTasks: number;
  };
  details?: CoordinationTask[];
}

// Script result type for internal use
interface ScriptResult {
  success: boolean;
  tasks?: CoordinationTask[];
  status?: CoordinationStatus;
  report?: CoordinationReport;
  executionTime?: number;
  agentAssigned?: string;
  details?: Record<string, unknown>;
  error?: string;
}

export async function listCoordinationTasks(filters: CoordinationTaskFilters = {}): Promise<CoordinationTask[]> {
  try {
    const args = ['list'];
    if (filters.priority) args.push('--priority', filters.priority);
    if (filters.agentType) args.push('--agent-type', filters.agentType);
    if (filters.status) args.push('--status', filters.status);

    const result = await runCoordinationScript(args);

    if (result.success) {
      return result.tasks || [];
    } else {
      console.warn('Failed to list coordination tasks:', result.error);
      return [];
    }
  } catch (error) {
    console.warn('Error listing coordination tasks:', error);
    return [];
  }
}

export async function executeCoordinationTask(options: CoordinationTaskExecution): Promise<TaskExecutionResult> {
  try {
    const args = ['execute', options.taskId];
    if (options.dryRun) args.push('--dry-run');
    if (options.force) args.push('--force');
    if (options.parallel) args.push('--parallel');

    const result = await runCoordinationScript(args);

    if (result.success) {
      return {
        success: true,
        taskId: options.taskId,
        status: typeof result.status === 'object' ? 'completed' : (result.status as string) || 'completed',
        executionTime: result.executionTime,
        agentAssigned: result.agentAssigned,
        details: result.details
      };
    } else {
      return {
        success: false,
        taskId: options.taskId,
        error: result.error,
        details: result.details
      };
    }
  } catch (error) {
    return {
      success: false,
      taskId: options.taskId,
      error: error instanceof Error ? error.message : 'Unknown error occurred'
    };
  }
}

export async function getCoordinationStatus(options: CoordinationStatusOptions = {}): Promise<CoordinationStatus | CoordinationTask[]> {
  try {
    const args = ['status'];
    if (options.taskId) args.push('--task-id', options.taskId);
    if (options.verbose) args.push('--verbose');
    if (options.progress) args.push('--progress');

    const result = await runCoordinationScript(args);

    if (result.success) {
      return result.status || result.tasks || {};
    } else {
      console.warn('Failed to get coordination status:', result.error);
      return {};
    }
  } catch (error) {
    console.warn('Error getting coordination status:', error);
    return {};
  }
}

export async function generateCoordinationReport(options: CoordinationReportOptions): Promise<CoordinationReport> {
  try {
    const args = ['report', '--format', options.format, '--period', options.period.toString()];
    if (options.includeCompleted) args.push('--include-completed');

    const result = await runCoordinationScript(args);

    if (result.success) {
      return result.report || { period: options.period, format: options.format };
    } else {
      throw new Error(result.error || 'Failed to generate report');
    }
  } catch (error) {
    throw new Error(error instanceof Error ? error.message : 'Failed to generate coordination report');
  }
}

async function runCoordinationScript(args: string[]): Promise<ScriptResult> {
  return new Promise((resolve, reject) => {
    // Path to the Python coordination script
    let scriptPath = path.join(__dirname, 'coordinationManager.py');
    if (!require('fs').existsSync(scriptPath)) {
      // Try the src path from dist
      scriptPath = path.join(__dirname, '../../src/services/coordinationManager.py');
    }

    const pythonProcess = spawn('python3', [scriptPath, ...args], {
      stdio: ['pipe', 'pipe', 'pipe'],
      cwd: path.dirname(scriptPath),
    });

    let stdout = '';
    let stderr = '';

    pythonProcess.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    pythonProcess.on('close', (code) => {
      if (code === 0) {
        try {
          const result = JSON.parse(stdout.trim());
          resolve(result);
        } catch (e) {
          reject(new Error(`Failed to parse Python output: ${stdout}`));
        }
      } else {
        reject(new Error(`Python script failed with code ${code}: ${stderr}`));
      }
    });

    pythonProcess.on('error', (error) => {
      reject(error);
    });
  });
}
