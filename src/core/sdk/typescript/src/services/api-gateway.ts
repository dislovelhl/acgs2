/**
 * ACGS-2 API Gateway Service
 * Constitutional Hash: cdd01ef066bc6cf2
 */

import { ACGS2Client } from '../client';
import { CONSTITUTIONAL_HASH } from '../types';
import { ValidationError } from '../utils';

// =============================================================================
// Types
// =============================================================================

export interface HealthCheckResponse {
  status: string;
  version?: string;
  timestamp: string;
  constitutionalHash: string;
}

export interface FeedbackRequest {
  userId: string;
  category: 'bug' | 'feature' | 'general' | 'performance' | 'security';
  rating: number; // 1-5
  title: string;
  description?: string;
  metadata?: Record<string, any>;
}

export interface FeedbackResponse {
  id: string;
  status: 'received' | 'processing' | 'completed';
  timestamp: string;
}

export interface FeedbackStats {
  totalFeedback: number;
  averageRating: number;
  categoryBreakdown: Record<string, number>;
  recentFeedback: FeedbackSummary[];
}

export interface FeedbackSummary {
  id: string;
  userId: string;
  category: string;
  rating: number;
  title: string;
  timestamp: string;
}

export interface ServiceInfo {
  name: string;
  version: string;
  status: 'healthy' | 'degraded' | 'unhealthy';
  endpoints: string[];
  description?: string;
}

export interface ServicesResponse {
  services: ServiceInfo[];
  gateway: {
    version: string;
    uptime: number;
    activeConnections: number;
  };
}

// =============================================================================
// API Gateway Service
// =============================================================================

export class APIGatewayService {
  constructor(private readonly client: ACGS2Client) {}

  // ===========================================================================
  // Health & Status
  // ===========================================================================

  /**
   * Check API gateway health
   */
  async healthCheck(): Promise<HealthCheckResponse> {
    const response = await this.client.get<HealthCheckResponse>('/health');

    if (!response.success || !response.data) {
      throw new ValidationError('Health check failed');
    }

    return response.data;
  }

  // ===========================================================================
  // Feedback
  // ===========================================================================

  /**
   * Submit user feedback
   */
  async submitFeedback(request: FeedbackRequest): Promise<FeedbackResponse> {
    const response = await this.client.post<FeedbackResponse>('/feedback', {
      ...request,
      constitutionalHash: CONSTITUTIONAL_HASH,
    });

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to submit feedback');
    }

    return response.data;
  }

  /**
   * Get feedback statistics
   */
  async getFeedbackStats(): Promise<FeedbackStats> {
    const response = await this.client.get<FeedbackStats>('/feedback/stats');

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to get feedback stats');
    }

    return response.data;
  }

  // ===========================================================================
  // Service Discovery
  // ===========================================================================

  /**
   * List available services
   */
  async listServices(): Promise<ServicesResponse> {
    const response = await this.client.get<ServicesResponse>('/services');

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to list services');
    }

    return response.data;
  }
}
