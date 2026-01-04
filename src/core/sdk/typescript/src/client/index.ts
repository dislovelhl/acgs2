/**
 * ACGS-2 TypeScript SDK HTTP Client
 * Constitutional Hash: cdd01ef066bc6cf2
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';
import {
  CONSTITUTIONAL_HASH,
  ACGS2Config,
  ApiResponse,
  ApiError,
} from '../types';
import {
  assertConstitutionalHash,
  generateUUID,
  nowISO,
  withRetry,
  RetryOptions,
  joinUrl,
  buildQueryString,
  ACGS2Error,
  AuthenticationError,
  AuthorizationError,
  NetworkError,
  RateLimitError,
  TimeoutError,
  ValidationError,
  Logger,
  createLogger,
  silentLogger,
} from '../utils';

// =============================================================================
// Client Configuration
// =============================================================================

export interface ClientConfig extends ACGS2Config {
  logger?: Logger;
  retryOptions?: Partial<RetryOptions>;
}

const defaultConfig: Partial<ClientConfig> = {
  timeout: 30000,
  retryAttempts: 3,
  retryDelay: 1000,
  validateConstitutionalHash: true,
};

// =============================================================================
// HTTP Client
// =============================================================================

export class ACGS2Client {
  private readonly client: AxiosInstance;
  private readonly config: ClientConfig;
  private readonly logger: Logger;
  private accessToken?: string;
  private refreshToken?: string;

  constructor(config: ClientConfig) {
    this.config = { ...defaultConfig, ...config };
    this.logger = config.logger ?? (process.env['NODE_ENV'] === 'development' ? createLogger() : silentLogger);
    this.accessToken = config.accessToken;

    // Create axios instance
    this.client = axios.create({
      baseURL: this.config.baseUrl,
      timeout: this.config.timeout,
      headers: {
        'Content-Type': 'application/json',
        'X-Constitutional-Hash': CONSTITUTIONAL_HASH,
        'X-SDK-Version': '2.0.0',
        'X-SDK-Language': 'typescript',
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        // Add request ID
        config.headers['X-Request-ID'] = generateUUID();

        // Add authentication
        if (this.accessToken) {
          config.headers['Authorization'] = `Bearer ${this.accessToken}`;
        } else if (this.config.apiKey) {
          config.headers['X-API-Key'] = this.config.apiKey;
        }

        // Add tenant ID if configured
        if (this.config.tenantId) {
          config.headers['X-Tenant-ID'] = this.config.tenantId;
        }

        this.logger.debug(`Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        this.logger.error('Request error:', error);
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => {
        this.logger.debug(`Response: ${response.status} ${response.config.url}`);

        // Validate constitutional hash if enabled
        if (this.config.validateConstitutionalHash) {
          const responseHash = response.data?.constitutionalHash;
          if (responseHash && responseHash !== CONSTITUTIONAL_HASH) {
            const error = new ACGS2Error(
              'Constitutional hash mismatch in response',
              'CONSTITUTIONAL_HASH_MISMATCH'
            );
            this.config.onConstitutionalViolation?.(CONSTITUTIONAL_HASH, responseHash);
            return Promise.reject(error);
          }
        }

        return response;
      },
      async (error: AxiosError) => {
        return this.handleError(error);
      }
    );
  }

  // ===========================================================================
  // Authentication
  // ===========================================================================

  /**
   * Sets the access token for authenticated requests
   */
  setAccessToken(token: string): void {
    this.accessToken = token;
  }

  /**
   * Clears authentication tokens
   */
  clearAuth(): void {
    this.accessToken = undefined;
    this.refreshToken = undefined;
  }

  /**
   * Checks if client is authenticated
   */
  isAuthenticated(): boolean {
    return !!this.accessToken;
  }

  // ===========================================================================
  // HTTP Methods
  // ===========================================================================

  /**
   * Performs a GET request
   */
  async get<T>(
    path: string,
    params?: Record<string, unknown>,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    const url = params ? `${path}${buildQueryString(params)}` : path;
    return this.request<T>('GET', url, undefined, config);
  }

  /**
   * Performs a POST request
   */
  async post<T>(
    path: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    return this.request<T>('POST', path, data, config);
  }

  /**
   * Performs a PUT request
   */
  async put<T>(
    path: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    return this.request<T>('PUT', path, data, config);
  }

  /**
   * Performs a PATCH request
   */
  async patch<T>(
    path: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    return this.request<T>('PATCH', path, data, config);
  }

  /**
   * Performs a DELETE request
   */
  async delete<T>(
    path: string,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    return this.request<T>('DELETE', path, undefined, config);
  }

  // ===========================================================================
  // Core Request Handler
  // ===========================================================================

  private async request<T>(
    method: string,
    path: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    const requestFn = async (): Promise<ApiResponse<T>> => {
      const response = await this.client.request<ApiResponse<T>>({
        method,
        url: path,
        data,
        ...config,
      });
      return response.data;
    };

    // Apply retry logic for transient errors
    const retryOptions: Partial<RetryOptions> = {
      maxAttempts: this.config.retryAttempts,
      baseDelay: this.config.retryDelay,
      retryCondition: (error) => {
        if (error instanceof NetworkError) {
          // Retry on network errors and 5xx status codes
          return !error.statusCode || error.statusCode >= 500;
        }
        if (error instanceof RateLimitError) {
          return true;
        }
        return false;
      },
      ...this.config.retryOptions,
    };

    return withRetry(requestFn, retryOptions);
  }

  // ===========================================================================
  // Error Handling
  // ===========================================================================

  private async handleError(error: AxiosError): Promise<never> {
    const response = error.response;
    const apiError = response?.data as ApiResponse<unknown> | undefined;

    // Log error
    this.logger.error(`API Error: ${error.message}`, {
      status: response?.status,
      url: error.config?.url,
      error: apiError?.error,
    });

    // Call error handler if configured
    if (apiError?.error) {
      this.config.onError?.(apiError.error);
    }

    // Handle specific error types
    if (!response) {
      if (error.code === 'ECONNABORTED') {
        throw new TimeoutError('Request timed out');
      }
      throw new NetworkError(`Network error: ${error.message}`);
    }

    const status = response.status;
    const errorMessage = apiError?.error?.message || error.message;

    switch (status) {
      case 401:
        throw new AuthenticationError(errorMessage);
      case 403:
        throw new AuthorizationError(errorMessage);
      case 422:
        throw new ValidationError(errorMessage, apiError?.error?.details as Record<string, string[]>);
      case 429:
        const retryAfter = parseInt(response.headers['retry-after'] || '60', 10);
        throw new RateLimitError(errorMessage, retryAfter);
      default:
        throw new NetworkError(errorMessage, status);
    }
  }

  // ===========================================================================
  // Health Check
  // ===========================================================================

  /**
   * Checks API health and connectivity
   */
  async healthCheck(): Promise<{
    healthy: boolean;
    latencyMs: number;
    constitutionalHash: string;
    version?: string;
  }> {
    const start = Date.now();
    try {
      const response = await this.get<{ version: string; constitutionalHash: string }>('/health');
      const latencyMs = Date.now() - start;

      return {
        healthy: response.success,
        latencyMs,
        constitutionalHash: response.constitutionalHash,
        version: response.data?.version,
      };
    } catch (error) {
      const latencyMs = Date.now() - start;
      return {
        healthy: false,
        latencyMs,
        constitutionalHash: CONSTITUTIONAL_HASH,
      };
    }
  }
}

// =============================================================================
// Factory Function
// =============================================================================

/**
 * Creates a configured ACGS2Client instance
 */
export function createClient(config: ClientConfig): ACGS2Client {
  return new ACGS2Client(config);
}

// =============================================================================
// Export Types
// =============================================================================
