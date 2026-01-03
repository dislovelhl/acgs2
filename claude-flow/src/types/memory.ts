/**
 * Interface for memory service configuration
 */
export interface MemoryConfig {
  url: string;
  password?: string;
  defaultTtlSeconds?: number;
  maxReconnectAttempts?: number;
}

/**
 * Interface for memory entries
 */
export interface MemoryEntry<T = any> {
  key: string;
  value: T;
  timestamp: number;
  ttl?: number;
}

/**
 * Interface for memory search results
 */
export interface MemorySearchResult {
  cursor: number;
  keys: string[];
}
