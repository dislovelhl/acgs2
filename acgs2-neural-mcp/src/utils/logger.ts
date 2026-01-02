/**
 * ACGS-2 Neural MCP Structured Logging Configuration
 *
 * Enterprise-grade structured logging with JSON formatting, correlation ID support,
 * and RFC 5424 severity levels for MCP server operations.
 *
 * This module provides:
 *   - JSON-formatted log output for enterprise observability (Splunk, ELK, Datadog)
 *   - Correlation ID binding for request tracing
 *   - RFC 5424 severity levels (debug, info, warn, error)
 *   - Console-friendly output for local development
 *   - Convenience functions for structured logging
 *
 * Usage:
 *   import { getLogger, configureLogging, LogLevel } from './utils/logger.js';
 *
 *   // Configure logging at startup (optional - uses defaults)
 *   configureLogging({ serviceName: 'acgs2-neural-mcp', logLevel: 'info' });
 *
 *   // Get a logger instance
 *   const logger = getLogger('neural/mapper');
 *   logger.info('domain_loaded', { domainId: 'abc123', nodeCount: 15 });
 *
 * Example output (JSON format):
 *   {"timestamp":"2024-01-02T15:00:00.000Z","level":"info","service":"acgs2-neural-mcp","logger":"neural/mapper","message":"domain_loaded","domainId":"abc123","nodeCount":15}
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
  /** Service name for log identification (default: 'acgs2-neural-mcp') */
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
let _serviceName = 'acgs2-neural-mcp';
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
 *   serviceName: 'acgs2-neural-mcp',
 *   logLevel: 'debug',
 *   jsonFormat: true
 * });
 */
export function configureLogging(config: LoggingConfig = {}): void {
  if (_configured && _baseLogger) {
    return;
  }

  const {
    serviceName = process.env.SERVICE_NAME || 'acgs2-neural-mcp',
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
 * const logger = getLogger('neural/mapper');
 * logger.info('domain_loaded', { domainId: 'abc123', nodeCount: 15 });
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
 * For MCP operations, this can be used to track a specific request execution.
 *
 * @param correlationId - Unique identifier for the operation
 *
 * @example
 * bindCorrelationId(crypto.randomUUID());
 * logger.info('tool_called', { tool: 'neural_train' });
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
 *   await mapper.train(data);
 * } catch (error) {
 *   logError(logger, 'training_failed', error, { epochs: 100 });
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
 * logSuccess(logger, 'domains_loaded', { nodeCount: 15, edgeCount: 20 });
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
 * logWarning(logger, 'low_accuracy', { accuracy: 0.65, threshold: 0.8 });
 */
export function logWarning(logger: StructuredLogger, event: string, context?: Record<string, unknown>): void {
  logger.warn(event, context);
}

// ============================================================================
// MCP-Specific Utilities
// ============================================================================

/**
 * Create a logger for MCP tool execution.
 *
 * Automatically binds a correlation ID for the request session.
 *
 * @param toolName - Name of the MCP tool being executed
 * @returns Logger configured for the tool
 *
 * @example
 * const logger = createToolLogger('neural_train');
 * logger.info('tool_started');
 * // ... execute tool
 * logger.info('tool_completed', { duration_ms: 150 });
 */
export function createToolLogger(toolName: string): StructuredLogger {
  // Generate correlation ID for this tool execution
  const correlationId = `tool-${Date.now().toString(36)}-${Math.random().toString(36).substr(2, 9)}`;
  bindCorrelationId(correlationId);

  const logger = getLogger(`tools/${toolName.replace(/\s+/g, '-')}`);
  return logger.child({ tool: toolName, correlation_id: correlationId });
}

/**
 * Log the start of an MCP tool call.
 *
 * @param logger - Logger instance
 * @param args - Tool arguments
 *
 * @example
 * logToolStart(logger, { epochs: 100, learningRate: 0.001 });
 */
export function logToolStart(logger: StructuredLogger, args?: Record<string, unknown>): void {
  logger.info('tool_started', { args });
}

/**
 * Log the completion of an MCP tool call.
 *
 * @param logger - Logger instance
 * @param durationMs - Duration of tool execution in milliseconds
 * @param result - Result context
 *
 * @example
 * logToolComplete(logger, 150, { accuracy: 0.95 });
 */
export function logToolComplete(
  logger: StructuredLogger,
  durationMs: number,
  result?: Record<string, unknown>
): void {
  logger.info('tool_completed', { duration_ms: durationMs, success: true, ...result });
}

/**
 * Log the failure of an MCP tool call.
 *
 * @param logger - Logger instance
 * @param durationMs - Duration of tool execution in milliseconds
 * @param error - Error that caused the failure
 *
 * @example
 * logToolFailure(logger, 50, new Error('Invalid domain configuration'));
 */
export function logToolFailure(logger: StructuredLogger, durationMs: number, error?: Error | unknown): void {
  const context: Record<string, unknown> = { duration_ms: durationMs, success: false };

  if (error instanceof Error) {
    context.error_type = error.name;
    context.error_message = error.message;
  } else if (error) {
    context.error_message = String(error);
  }

  logger.error('tool_failed', context);
}

/**
 * Create a logger for MCP server lifecycle events.
 *
 * @param serverName - Name of the MCP server
 * @returns Logger configured for server events
 *
 * @example
 * const logger = createServerLogger('acgs2-neural-mcp');
 * logger.info('server_started', { version: '2.0.0' });
 */
export function createServerLogger(serverName: string): StructuredLogger {
  return getLogger(`server/${serverName}`);
}

/**
 * Log server startup event.
 *
 * @param logger - Logger instance
 * @param version - Server version
 * @param context - Additional context fields
 *
 * @example
 * logServerStart(logger, '2.0.0', { transport: 'stdio' });
 */
export function logServerStart(logger: StructuredLogger, version: string, context?: Record<string, unknown>): void {
  logger.info('server_started', { version, ...context });
}

/**
 * Log server shutdown event.
 *
 * @param logger - Logger instance
 * @param reason - Reason for shutdown
 * @param context - Additional context fields
 *
 * @example
 * logServerShutdown(logger, 'signal', { signal: 'SIGTERM' });
 */
export function logServerShutdown(logger: StructuredLogger, reason: string, context?: Record<string, unknown>): void {
  logger.info('server_shutdown', { reason, ...context });
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
  createToolLogger,
  logToolStart,
  logToolComplete,
  logToolFailure,
  createServerLogger,
  logServerStart,
  logServerShutdown,
};
