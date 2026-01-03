/**
 * ACGS-2 HTTP Client with Enterprise Features
 * Constitutional Hash: cdd01ef066bc6cf2
 */

import axios, {
  AxiosInstance,
  AxiosRequestConfig,
  AxiosResponse,
  AxiosError,
  InternalAxiosRequestConfig,
} from 'axios';
import { z } from 'zod';
import { TenantContext } from './tenant';
import { SDKConfig } from './client';

// HTTP client configuration schema
export const HttpClientConfigSchema = z.object({
  timeout: z.number().min(1000).max(30000),
  retryAttempts: z.number().min(0).max(5),
  retryDelay: z.number().min(100).max(5000),
  retryOnStatusCodes: z.array(z.number()).default([429, 500, 502, 503, 504]),
  enableMetrics: z.boolean().default(true),
  enableTracing: z.boolean().default(true),
  userAgent: z.string().default('ACGS-2-TypeScript-SDK/3.0.0'),
});

export type HttpClientConfig = z.infer<typeof HttpClientConfigSchema>;

// Request/response interceptors
export interface RequestInterceptor {
  (config: InternalAxiosRequestConfig): InternalAxiosRequestConfig | Promise<InternalAxiosRequestConfig>;
}

export interface ResponseInterceptor {
  (response: AxiosResponse): AxiosResponse | Promise<AxiosResponse>;
}

export interface ErrorInterceptor {
  (error: AxiosError): Promise<never>;
}

// Metrics and tracing
export interface RequestMetrics {
  method: string;
  url: string;
  statusCode?: number;
  duration: number;
  retryCount: number;
  timestamp: Date;
  tenantId: string;
  userId?: string;
  error?: string;
}

export interface TracingHeaders {
  'x-trace-id': string;
  'x-span-id': string;
  'x-parent-span-id'?: string;
}

/**
 * Enterprise HTTP Client with retry logic, metrics, and tenant context
 */
export class EnterpriseHttpClient {
  private readonly axiosInstance: AxiosInstance;
  private readonly config: HttpClientConfig;
  private tenantContext?: TenantContext;
  private requestMetrics: RequestMetrics[] = [];
  private maxMetricsHistory = 1000;

  // Interceptors
  private requestInterceptors: RequestInterceptor[] = [];
  private responseInterceptors: ResponseInterceptor[] = [];
  private errorInterceptors: ErrorInterceptor[] = [];

  constructor(
    baseURL: string,
    config: HttpClientConfig,
    private onError?: (error: any) => void
  ) {
    this.config = HttpClientConfigSchema.parse(config);

    // Create axios instance
    this.axiosInstance = axios.create({
      baseURL,
      timeout: this.config.timeout,
      headers: {
        'User-Agent': this.config.userAgent,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });

    // Set up default interceptors
    this.setupDefaultInterceptors();
  }

  /**
   * Set tenant context for requests
   */
  setTenantContext(context: TenantContext): void {
    this.tenantContext = context;
  }

  /**
   * Add request interceptor
   */
  addRequestInterceptor(interceptor: RequestInterceptor): void {
    this.requestInterceptors.push(interceptor);
  }

  /**
   * Add response interceptor
   */
  addResponseInterceptor(interceptor: ResponseInterceptor): void {
    this.responseInterceptors.push(interceptor);
  }

  /**
   * Add error interceptor
   */
  addErrorInterceptor(interceptor: ErrorInterceptor): void {
    this.errorInterceptors.push(interceptor);
  }

  /**
   * Make HTTP request
   */
  async request<T = any>(config: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    const startTime = Date.now();
    let retryCount = 0;
    let lastError: AxiosError | null = null;

    // Inject tenant context and tracing
    const enrichedConfig = this.enrichRequestConfig(config);

    while (retryCount <= this.config.retryAttempts) {
      try {
        const response = await this.axiosInstance.request<T>(enrichedConfig);

        // Record metrics
        this.recordMetrics({
          method: config.method?.toUpperCase() || 'GET',
          url: config.url || '',
          statusCode: response.status,
          duration: Date.now() - startTime,
          retryCount,
          timestamp: new Date(),
          tenantId: this.tenantContext?.tenantId || 'unknown',
          userId: this.tenantContext?.userId,
        });

        return response;

      } catch (error) {
        lastError = error as AxiosError;
        const shouldRetry = this.shouldRetry(error as AxiosError, retryCount);

        if (shouldRetry && retryCount < this.config.retryAttempts) {
          retryCount++;
          const delay = this.calculateRetryDelay(retryCount);
          await this.delay(delay);
          continue;
        }

        // Record failed request metrics
        this.recordMetrics({
          method: config.method?.toUpperCase() || 'GET',
          url: config.url || '',
          duration: Date.now() - startTime,
          retryCount,
          timestamp: new Date(),
          tenantId: this.tenantContext?.tenantId || 'unknown',
          userId: this.tenantContext?.userId,
          error: lastError.message,
        });

        // Call error handler
        if (this.onError) {
          this.onError(lastError);
        }

        throw lastError;
      }
    }

    throw lastError;
  }

  /**
   * GET request
   */
  async get<T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.request<T>({ ...config, method: 'GET', url });
  }

  /**
   * POST request
   */
  async post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.request<T>({ ...config, method: 'POST', url, data });
  }

  /**
   * PUT request
   */
  async put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.request<T>({ ...config, method: 'PUT', url, data });
  }

  /**
   * PATCH request
   */
  async patch<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.request<T>({ ...config, method: 'PATCH', url, data });
  }

  /**
   * DELETE request
   */
  async delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.request<T>({ ...config, method: 'DELETE', url });
  }

  /**
   * Get request metrics
   */
  getMetrics(): RequestMetrics[] {
    return [...this.requestMetrics];
  }

  /**
   * Clear metrics history
   */
  clearMetrics(): void {
    this.requestMetrics = [];
  }

  /**
   * Get client statistics
   */
  getStats(): {
    totalRequests: number;
    successRate: number;
    averageResponseTime: number;
    errorRate: number;
    recentErrors: RequestMetrics[];
  } {
    const totalRequests = this.requestMetrics.length;
    const successfulRequests = this.requestMetrics.filter(m => !m.error).length;
    const successRate = totalRequests > 0 ? successfulRequests / totalRequests : 0;

    const responseTimes = this.requestMetrics
      .filter(m => m.statusCode && m.statusCode < 400)
      .map(m => m.duration);
    const averageResponseTime = responseTimes.length > 0
      ? responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length
      : 0;

    const errorRate = 1 - successRate;
    const recentErrors = this.requestMetrics
      .filter(m => m.error)
      .slice(-10);

    return {
      totalRequests,
      successRate,
      averageResponseTime,
      errorRate,
      recentErrors,
    };
  }

  /**
   * Setup default interceptors
   */
  private setupDefaultInterceptors(): void {
    // Request interceptor for tenant context and tracing
    this.axiosInstance.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        // Add tenant headers
        if (this.tenantContext) {
          const tenantHeaders = this.tenantContext.getHeaders();
          config.headers = { ...config.headers, ...tenantHeaders };
        }

        // Add tracing headers
        if (this.config.enableTracing) {
          const tracingHeaders = this.generateTracingHeaders();
          config.headers = { ...config.headers, ...tracingHeaders };
        }

        // Add timestamp for metrics
        (config as any)._startTime = Date.now();

        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for metrics
    this.axiosInstance.interceptors.response.use(
      (response) => {
        // Apply custom response interceptors
        for (const interceptor of this.responseInterceptors) {
          response = interceptor(response);
        }
        return response;
      },
      async (error) => {
        // Apply custom error interceptors
        for (const interceptor of this.errorInterceptors) {
          try {
            await interceptor(error);
          } catch (interceptorError) {
            // If interceptor throws, continue with original error
          }
        }
        return Promise.reject(error);
      }
    );
  }

  /**
   * Enrich request config with tenant context and tracing
   */
  private enrichRequestConfig(config: AxiosRequestConfig): AxiosRequestConfig {
    const enrichedConfig = { ...config };

    // Add tenant headers
    if (this.tenantContext) {
      enrichedConfig.headers = {
        ...enrichedConfig.headers,
        ...this.tenantContext.getHeaders(),
      };
    }

    // Add tracing headers
    if (this.config.enableTracing) {
      enrichedConfig.headers = {
        ...enrichedConfig.headers,
        ...this.generateTracingHeaders(),
      };
    }

    return enrichedConfig;
  }

  /**
   * Generate tracing headers
   */
  private generateTracingHeaders(): TracingHeaders {
    const traceId = this.generateId();
    const spanId = this.generateId();

    return {
      'x-trace-id': traceId,
      'x-span-id': spanId,
    };
  }

  /**
   * Generate random ID for tracing
   */
  private generateId(): string {
    return Math.random().toString(36).substring(2, 15) +
           Math.random().toString(36).substring(2, 15);
  }

  /**
   * Determine if request should be retried
   */
  private shouldRetry(error: AxiosError, retryCount: number): boolean {
    if (retryCount >= this.config.retryAttempts) {
      return false;
    }

    if (!error.response) {
      // Network errors are retryable
      return true;
    }

    const statusCode = error.response.status;
    return this.config.retryOnStatusCodes.includes(statusCode);
  }

  /**
   * Calculate retry delay with exponential backoff
   */
  private calculateRetryDelay(retryCount: number): number {
    const baseDelay = this.config.retryDelay;
    const exponentialDelay = baseDelay * Math.pow(2, retryCount - 1);
    const jitter = Math.random() * 0.1 * exponentialDelay;
    return Math.min(exponentialDelay + jitter, 30000); // Max 30 seconds
  }

  /**
   * Record request metrics
   */
  private recordMetrics(metrics: RequestMetrics): void {
    this.requestMetrics.push(metrics);

    // Keep only recent metrics
    if (this.requestMetrics.length > this.maxMetricsHistory) {
      this.requestMetrics = this.requestMetrics.slice(-this.maxMetricsHistory);
    }
  }

  /**
   * Delay utility
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

/**
 * Create HTTP client instance
 */
export function createHttpClient(
  sdkConfig: SDKConfig,
  onError?: (error: any) => void
): AxiosInstance {
  const httpConfig: HttpClientConfig = {
    timeout: sdkConfig.timeout,
    retryAttempts: sdkConfig.retryAttempts,
    retryDelay: sdkConfig.retryDelay,
    enableMetrics: sdkConfig.enableMetrics,
    enableTracing: sdkConfig.enableTracing,
  };

  const client = new EnterpriseHttpClient(sdkConfig.baseURL, httpConfig, onError);

  // Return axios-compatible interface
  return {
    request: client.request.bind(client),
    get: client.get.bind(client),
    post: client.post.bind(client),
    put: client.put.bind(client),
    patch: client.patch.bind(client),
    delete: client.delete.bind(client),

    // Additional methods for enterprise features
    setTenantContext: client.setTenantContext.bind(client),
    getMetrics: client.getMetrics.bind(client),
    getStats: client.getStats.bind(client),
    clearMetrics: client.clearMetrics.bind(client),

    // Interceptor methods
    interceptors: {
      request: {
        use: (interceptor: RequestInterceptor) => {
          client.addRequestInterceptor(interceptor);
          return { eject: () => {} }; // Mock eject function
        },
      },
      response: {
        use: (
          successInterceptor: ResponseInterceptor,
          errorInterceptor?: ErrorInterceptor
        ) => {
          if (successInterceptor) {
            client.addResponseInterceptor(successInterceptor);
          }
          if (errorInterceptor) {
            client.addErrorInterceptor(errorInterceptor);
          }
          return { eject: () => {} }; // Mock eject function
        },
      },
    },

    // Default axios properties
    defaults: {
      timeout: httpConfig.timeout,
      headers: {
        common: {
          'User-Agent': httpConfig.userAgent,
        },
      },
    },
  } as AxiosInstance;
}
