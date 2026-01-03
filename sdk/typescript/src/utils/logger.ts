/**
 * ACGS-2 TypeScript Logger Utility
 * Constitutional Hash: cdd01ef066bc6cf2
 *
 * Structured logging utility to replace console.log statements throughout the codebase.
 */

export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
}

export interface LogEntry {
  timestamp: string;
  level: string;
  logger: string;
  message: string;
  constitutional_hash: string;
  data?: any;
}

export class Logger {
  private name: string;
  private level: LogLevel;
  private constitutionalHash = "cdd01ef066bc6cf2";

  constructor(name: string, level: LogLevel = LogLevel.INFO) {
    this.name = name;
    this.level = level;
  }

  private shouldLog(level: LogLevel): boolean {
    return level >= this.level;
  }

  private formatMessage(level: string, message: string, data?: any): LogEntry {
    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level,
      logger: this.name,
      message,
      constitutional_hash: this.constitutionalHash,
    };

    if (data !== undefined) {
      entry.data = data;
    }

    return entry;
  }

  private log(level: LogLevel, levelName: string, message: string, data?: any): void {
    if (!this.shouldLog(level)) {
      return;
    }

    const entry = this.formatMessage(levelName, message, data);

    // Use console methods for appropriate levels
    switch (level) {
      case LogLevel.DEBUG:
        console.debug(JSON.stringify(entry));
        break;
      case LogLevel.INFO:
        console.info(JSON.stringify(entry));
        break;
      case LogLevel.WARN:
        console.warn(JSON.stringify(entry));
        break;
      case LogLevel.ERROR:
        console.error(JSON.stringify(entry));
        break;
    }
  }

  debug(message: string, data?: any): void {
    this.log(LogLevel.DEBUG, 'DEBUG', message, data);
  }

  info(message: string, data?: any): void {
    this.log(LogLevel.INFO, 'INFO', message, data);
  }

  warn(message: string, data?: any): void {
    this.log(LogLevel.WARN, 'WARN', message, data);
  }

  error(message: string, data?: any): void {
    this.log(LogLevel.ERROR, 'ERROR', message, data);
  }

  // Convenience methods for replacing console.log patterns
  logSuccess(message: string, data?: any): void {
    this.info(message, { ...data, status: 'success' });
  }

  logError(message: string, error?: any): void {
    this.error(message, { error: error?.message || error });
  }

  logResult(result: any): void {
    this.info('Operation completed', { result });
  }
}

// Global logger instances
const loggers: Map<string, Logger> = new Map();

export function getLogger(name: string, level?: LogLevel): Logger {
  if (!loggers.has(name)) {
    loggers.set(name, new Logger(name, level));
  }
  return loggers.get(name)!;
}

// Default logger for backward compatibility
export const logger = getLogger('acgs2-typescript');

// Convenience functions to replace console.log patterns
export function logSuccessResult(logger: Logger, result: any): void {
  logger.logSuccess('Operation completed successfully', { result });
}

export function logErrorResult(logger: Logger, error: any): void {
  logger.logError('Operation failed', error);
}
