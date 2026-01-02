/**
 * ACGS-2 Claude Flow Structured Logging Configuration
 *
 * Enterprise-grade structured logging with JSON formatting, correlation ID support,
 * and RFC 5424 severity levels for CLI operations.
 *
 * This module provides:
 *   - JSON-formatted log output for enterprise observability (Splunk, ELK, Datadog)
 *   - Correlation ID binding for request tracing
 *   - RFC 5424 severity levels (debug, info, warn, error)
 *   - Console-friendly output for local development
 *   - Convenience functions for structured logging
 *
 * Usage:
 *   import { getLogger, configureLogging, LogLevel } from './utils/logging_config';
 *
 *   // Configure logging at startup (optional - uses defaults)
 *   configureLogging({ serviceName: 'claude-flow', logLevel: 'info' });
 *
 *   // Get a logger instance
 *   const logger = getLogger('commands/agent');
 *   logger.info('agent_spawned', { agentId: 'abc123', type: 'coder' });
 *
 * Example output (JSON format):
 *   {"timestamp":"2024-01-02T15:00:00.000Z","level":"info","service":"claude-flow","logger":"commands/agent","message":"agent_spawned","agentId":"abc123","type":"coder"}
 */

import winston from 'winston';

// ============================================================================
// Types and Interfaces
// ============================================================================

/**
 * Log levels following RFC 5424 severity levels (subset commonly used in applications)
 */
export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

/**
 * Configuration options for logging setup
 */
export interface LoggingConfig {
  /** Service name for log identification (default: 'claude-flow') */
  serviceName?: string;
  /** Minimum log level to output (default: 'info') */
  logLevel?: LogLevel;
  /** Whether to output JSON format (default: true for production, false for dev) */
  jsonFormat?: boolean;
  /** Whether to include timestamps (default: true) */
  timestamps?: boolean;
  /** Whether to colorize console output (default: true in dev) */
  colorize?: boolean;
}

/**
 * Logger interface with typed methods
 */
export interface StructuredLogger {
  debug(message: string, context?: Record<string, unknown>): void;
  info(message: string, context?: Record<string, unknown>): void;
  warn(message: string, context?: Record<string, unknown>): void;
  error(message: string, context?: Record<string, unknown>): void;
  child(context: Record<string, unknown>): StructuredLogger;
}

// ============================================================================
// Module State
// ============================================================================

let _configured = false;
let _serviceName = 'claude-flow';
let _baseLogger: winston.Logger | null = null;
let _correlationId: string | null = null;

// Cache for logger instances
const _loggerCache = new Map<string, StructuredLogger>();

// ============================================================================
// Configuration Functions
// ============================================================================

/**
 * Configure logging for the application.
 *
 * This function should be called ONCE at application startup.
 * Subsequent calls will be ignored to prevent reconfiguration.
 *
 * @param config - Configuration options
 *
 * @example
 * // Configure with custom settings
 * configureLogging({
 *   serviceName: 'claude-flow',
 *   logLevel: 'debug',
 *   jsonFormat: true
 * });
 */
export function configureLogging(config: LoggingConfig = {}): void {
  if (_configured && _baseLogger) {
    return;
  }

  const {
    serviceName = process.env.SERVICE_NAME || 'claude-flow',
    logLevel = (process.env.LOG_LEVEL?.toLowerCase() as LogLevel) || 'info',
    jsonFormat = process.env.LOG_FORMAT !== 'console',
    timestamps = true,
    colorize = !jsonFormat && process.env.NODE_ENV !== 'production',
  } = config;

  _serviceName = serviceName;

  // Create format array
  const formatters: winston.Logform.Format[] = [];

  // Add timestamp
  if (timestamps) {
    formatters.push(winston.format.timestamp({ format: 'iso' }));
  }

  // Add error stack formatting
  formatters.push(winston.format.errors({ stack: true }));

  // Add metadata flattening for structured logging
  formatters.push(
    winston.format((info) => {
      // Add service name to all logs
      info.service = _serviceName;

      // Add correlation ID if set
      if (_correlationId) {
        info.correlation_id = _correlationId;
      }

      return info;
    })()
  );

  // Choose output format
  if (jsonFormat) {
    formatters.push(winston.format.json());
  } else {
    // Console-friendly format for development
    formatters.push(
      winston.format.printf(({ timestamp, level, message, service, logger: loggerName, ...meta }) => {
        const metaStr = Object.keys(meta).length > 0 ? ` ${JSON.stringify(meta)}` : '';
        return `${timestamp} [${service}] ${level.toUpperCase()} [${loggerName || 'root'}] ${message}${metaStr}`;
      })
    );
    if (colorize) {
      formatters.unshift(winston.format.colorize({ all: true }));
    }
  }

  // Create winston logger
  _baseLogger = winston.createLogger({
    level: logLevel,
    format: winston.format.combine(...formatters),
    transports: [new winston.transports.Console()],
    defaultMeta: {},
  });

  _configured = true;
}

// ============================================================================
// Logger Factory
// ============================================================================

/**
 * Get a logger instance for the given module name.
 *
 * @param name - Logger name (typically module/file path)
 * @returns Configured logger instance
 *
 * @example
 * const logger = getLogger('commands/agent');
 * logger.info('agent_spawned', { agentId: 'abc123', type: 'coder' });
 */
export function getLogger(name: string): StructuredLogger {
  // Auto-configure if not done yet
  if (!_configured) {
    configureLogging();
  }

  // Check cache
  const cached = _loggerCache.get(name);
  if (cached) {
    return cached;
  }

  // Create wrapper around winston logger
  const winstonLogger = _baseLogger!.child({ logger: name });

  const logger: StructuredLogger = {
    debug(message: string, context?: Record<string, unknown>): void {
      winstonLogger.debug(message, context);
    },
    info(message: string, context?: Record<string, unknown>): void {
      winstonLogger.info(message, context);
    },
    warn(message: string, context?: Record<string, unknown>): void {
      winstonLogger.warn(message, context);
    },
    error(message: string, context?: Record<string, unknown>): void {
      winstonLogger.error(message, context);
    },
    child(childContext: Record<string, unknown>): StructuredLogger {
      const childWinston = winstonLogger.child(childContext);
      return createLoggerWrapper(childWinston);
    },
  };

  _loggerCache.set(name, logger);
  return logger;
}

/**
 * Create a wrapper around a winston logger instance
 */
function createLoggerWrapper(winstonLogger: winston.Logger): StructuredLogger {
  return {
    debug(message: string, context?: Record<string, unknown>): void {
      winstonLogger.debug(message, context);
    },
    info(message: string, context?: Record<string, unknown>): void {
      winstonLogger.info(message, context);
    },
    warn(message: string, context?: Record<string, unknown>): void {
      winstonLogger.warn(message, context);
    },
    error(message: string, context?: Record<string, unknown>): void {
      winstonLogger.error(message, context);
    },
    child(childContext: Record<string, unknown>): StructuredLogger {
      const childWinston = winstonLogger.child(childContext);
      return createLoggerWrapper(childWinston);
    },
  };
}

// ============================================================================
// Correlation ID Management
// ============================================================================

/**
 * Bind a correlation ID to the current context.
 *
 * For CLI operations, this can be used to track a specific command execution.
 *
 * @param correlationId - Unique identifier for the operation
 *
 * @example
 * bindCorrelationId(crypto.randomUUID());
 * logger.info('command_started', { command: 'agent spawn' });
 */
export function bindCorrelationId(correlationId: string): void {
  _correlationId = correlationId;
}

/**
 * Get the current correlation ID.
 *
 * @returns Current correlation ID or null if not set
 */
export function getCorrelationId(): string | null {
  return _correlationId;
}

/**
 * Clear the current correlation ID.
 */
export function clearCorrelationId(): void {
  _correlationId = null;
}

// ============================================================================
// Convenience Functions
// ============================================================================

/**
 * Log an error with optional exception information.
 *
 * @param logger - Logger instance
 * @param event - Event name describing the error
 * @param error - Optional error object
 * @param context - Additional context fields
 *
 * @example
 * try {
 *   await spawnAgent(options);
 * } catch (error) {
 *   logError(logger, 'agent_spawn_failed', error, { agentType: 'coder' });
 * }
 */
export function logError(
  logger: StructuredLogger,
  event: string,
  error?: Error | unknown,
  context?: Record<string, unknown>
): void {
  const errorContext: Record<string, unknown> = { ...context };

  if (error instanceof Error) {
    errorContext.error_type = error.name;
    errorContext.error_message = error.message;
    if (error.stack) {
      errorContext.stack_trace = error.stack;
    }
  } else if (error) {
    errorContext.error_message = String(error);
  }

  logger.error(event, errorContext);
}

/**
 * Log a successful operation with structured context.
 *
 * @param logger - Logger instance
 * @param event - Event name describing the success
 * @param context - Additional context fields
 *
 * @example
 * logSuccess(logger, 'agent_spawned', { agentId: 'abc123', type: 'coder' });
 */
export function logSuccess(logger: StructuredLogger, event: string, context?: Record<string, unknown>): void {
  logger.info(event, { success: true, ...context });
}

/**
 * Log a warning with structured context.
 *
 * @param logger - Logger instance
 * @param event - Event name describing the warning
 * @param context - Additional context fields
 *
 * @example
 * logWarning(logger, 'rate_limit_approaching', { currentRate: 95, limit: 100 });
 */
export function logWarning(logger: StructuredLogger, event: string, context?: Record<string, unknown>): void {
  logger.warn(event, context);
}

// ============================================================================
// CLI-Specific Utilities
// ============================================================================

/**
 * Create a logger for CLI command execution.
 *
 * Automatically binds a correlation ID for the command session.
 *
 * @param commandName - Name of the CLI command being executed
 * @returns Logger configured for the command
 *
 * @example
 * const logger = createCommandLogger('agent spawn');
 * logger.info('command_started');
 * // ... execute command
 * logger.info('command_completed', { duration_ms: 150 });
 */
export function createCommandLogger(commandName: string): StructuredLogger {
  // Generate correlation ID for this command execution
  const correlationId = `cmd-${Date.now().toString(36)}-${Math.random().toString(36).substr(2, 9)}`;
  bindCorrelationId(correlationId);

  const logger = getLogger(`command/${commandName.replace(/\s+/g, '-')}`);
  return logger.child({ command: commandName, correlation_id: correlationId });
}

/**
 * Log the start of a CLI command.
 *
 * @param logger - Logger instance
 * @param args - Command arguments
 *
 * @example
 * logCommandStart(logger, { type: 'coder', name: 'my-agent' });
 */
export function logCommandStart(logger: StructuredLogger, args?: Record<string, unknown>): void {
  logger.info('command_started', { args });
}

/**
 * Log the completion of a CLI command.
 *
 * @param logger - Logger instance
 * @param durationMs - Duration of command execution in milliseconds
 * @param result - Result context
 *
 * @example
 * logCommandComplete(logger, 150, { agentId: 'abc123' });
 */
export function logCommandComplete(
  logger: StructuredLogger,
  durationMs: number,
  result?: Record<string, unknown>
): void {
  logger.info('command_completed', { duration_ms: durationMs, success: true, ...result });
}

/**
 * Log the failure of a CLI command.
 *
 * @param logger - Logger instance
 * @param durationMs - Duration of command execution in milliseconds
 * @param error - Error that caused the failure
 *
 * @example
 * logCommandFailure(logger, 50, new Error('Connection refused'));
 */
export function logCommandFailure(logger: StructuredLogger, durationMs: number, error?: Error | unknown): void {
  const context: Record<string, unknown> = { duration_ms: durationMs, success: false };

  if (error instanceof Error) {
    context.error_type = error.name;
    context.error_message = error.message;
  } else if (error) {
    context.error_message = String(error);
  }

  logger.error('command_failed', context);
}

// ============================================================================
// Exports
// ============================================================================

export default {
  configureLogging,
  getLogger,
  bindCorrelationId,
  getCorrelationId,
  clearCorrelationId,
  logError,
  logSuccess,
  logWarning,
  createCommandLogger,
  logCommandStart,
  logCommandComplete,
  logCommandFailure,
};
