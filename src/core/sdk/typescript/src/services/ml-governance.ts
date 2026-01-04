/**
 * ACGS-2 ML Governance Service
 * Adaptive ML models with feedback loops and drift detection
 * Constitutional Hash: cdd01ef066bc6cf2
 */

import type { ACGS2Client } from '../client/index.js';
import { CONSTITUTIONAL_HASH } from '../types/index.js';
import type {
  ABNTest,
  CreateABNTestRequest,
  CreateMLModelRequest,
  DriftDetection,
  FeedbackSubmission,
  MLModel,
  MakePredictionRequest,
  ModelPrediction,
  PaginatedResponse,
  SubmitFeedbackRequest,
  UpdateMLModelRequest,
} from '../types/index.js';

export class MLGovernanceService {
  private client: ACGS2Client;
  private basePath = '/api/v1/ml-governance';

  constructor(client: ACGS2Client) {
    this.client = client;
  }

  async createModel(request: CreateMLModelRequest): Promise<MLModel> {
    const response = await this.client.post(`${this.basePath}/models`, {
      ...request,
      constitutionalHash: CONSTITUTIONAL_HASH,
    });
    return response.data as MLModel;
  }

  async getModel(modelId: string): Promise<MLModel> {
    const response = await this.client.get(`${this.basePath}/models/${modelId}`);
    return response.data as MLModel;
  }

  async listModels(params?: {
    page?: number;
    pageSize?: number;
    modelType?: string;
    framework?: string;
  }): Promise<PaginatedResponse<MLModel>> {
    const queryParams = new URLSearchParams();
    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.pageSize) queryParams.append('pageSize', params.pageSize.toString());
    if (params?.modelType) queryParams.append('modelType', params.modelType);
    if (params?.framework) queryParams.append('framework', params.framework);

    const response = await this.client.get(`${this.basePath}/models?${queryParams.toString()}`);
    return response.data as PaginatedResponse<MLModel>;
  }

  async updateModel(modelId: string, request: UpdateMLModelRequest): Promise<MLModel> {
    const response = await this.client.put(`${this.basePath}/models/${modelId}`, {
      ...request,
      constitutionalHash: CONSTITUTIONAL_HASH,
    });
    return response.data as MLModel;
  }

  async deleteModel(modelId: string): Promise<void> {
    await this.client.delete(`${this.basePath}/models/${modelId}`);
  }

  async makePrediction(request: MakePredictionRequest): Promise<ModelPrediction> {
    const response = await this.client.post(`${this.basePath}/predictions`, {
      ...request,
      constitutionalHash: CONSTITUTIONAL_HASH,
    });
    return response.data as ModelPrediction;
  }

  async getPrediction(predictionId: string): Promise<ModelPrediction> {
    const response = await this.client.get(`${this.basePath}/predictions/${predictionId}`);
    return response.data as ModelPrediction;
  }

  async listPredictions(params?: {
    modelId?: string;
    page?: number;
    pageSize?: number;
  }): Promise<PaginatedResponse<ModelPrediction>> {
    const queryParams = new URLSearchParams();
    if (params?.modelId) queryParams.append('modelId', params.modelId);
    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.pageSize) queryParams.append('pageSize', params.pageSize.toString());

    const response = await this.client.get(`${this.basePath}/predictions?${queryParams.toString()}`);
    return response.data as PaginatedResponse<ModelPrediction>;
  }

  async submitFeedback(request: SubmitFeedbackRequest): Promise<FeedbackSubmission> {
    const response = await this.client.post(`${this.basePath}/feedback`, {
      ...request,
      constitutionalHash: CONSTITUTIONAL_HASH,
    });
    return response.data as FeedbackSubmission;
  }

  async getFeedback(feedbackId: string): Promise<FeedbackSubmission> {
    const response = await this.client.get(`${this.basePath}/feedback/${feedbackId}`);
    return response.data as FeedbackSubmission;
  }

  async listFeedback(params?: {
    modelId?: string;
    feedbackType?: string;
    page?: number;
    pageSize?: number;
  }): Promise<PaginatedResponse<FeedbackSubmission>> {
    const queryParams = new URLSearchParams();
    if (params?.modelId) queryParams.append('modelId', params.modelId);
    if (params?.feedbackType) queryParams.append('feedbackType', params.feedbackType);
    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.pageSize) queryParams.append('pageSize', params.pageSize.toString());

    const response = await this.client.get(`${this.basePath}/feedback?${queryParams.toString()}`);
    return response.data as PaginatedResponse<FeedbackSubmission>;
  }

  async checkDrift(modelId: string): Promise<DriftDetection> {
    const response = await this.client.get(`${this.basePath}/models/${modelId}/drift`);
    return response.data as DriftDetection;
  }

  async retrainModel(
    modelId: string,
    options?: { feedbackThreshold?: number }
  ): Promise<Record<string, unknown>> {
    const payload: Record<string, unknown> = {
      constitutionalHash: CONSTITUTIONAL_HASH,
    };
    if (options?.feedbackThreshold) {
      payload['feedbackThreshold'] = options.feedbackThreshold;
    }

    const response = await this.client.post(`${this.basePath}/models/${modelId}/retrain`, payload);
    return response.data as Record<string, unknown>;
  }

  async createABNTest(request: CreateABNTestRequest): Promise<ABNTest> {
    const response = await this.client.post(`${this.basePath}/ab-tests`, {
      ...request,
      constitutionalHash: CONSTITUTIONAL_HASH,
    });
    return response.data as ABNTest;
  }

  async getABNTest(testId: string): Promise<ABNTest> {
    const response = await this.client.get(`${this.basePath}/ab-tests/${testId}`);
    return response.data as ABNTest;
  }

  async listABNTests(params?: {
    page?: number;
    pageSize?: number;
  }): Promise<PaginatedResponse<ABNTest>> {
    const queryParams = new URLSearchParams();
    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.pageSize) queryParams.append('pageSize', params.pageSize.toString());

    const response = await this.client.get(`${this.basePath}/ab-tests?${queryParams.toString()}`);
    return response.data as PaginatedResponse<ABNTest>;
  }

  async stopABNTest(testId: string): Promise<ABNTest> {
    const response = await this.client.post(`${this.basePath}/ab-tests/${testId}/stop`);
    return response.data as ABNTest;
  }

  async getABNTestResults(testId: string): Promise<Record<string, unknown>> {
    const response = await this.client.get(`${this.basePath}/ab-tests/${testId}/results`);
    return response.data as Record<string, unknown>;
  }

  async getModelMetrics(
    modelId: string,
    params?: { startDate?: string; endDate?: string }
  ): Promise<Record<string, unknown>> {
    const queryParams = new URLSearchParams();
    if (params?.startDate) queryParams.append('startDate', params.startDate);
    if (params?.endDate) queryParams.append('endDate', params.endDate);

    const response = await this.client.get(
      `${this.basePath}/models/${modelId}/metrics?${queryParams.toString()}`
    );
    return response.data as Record<string, unknown>;
  }

  async getDashboardData(): Promise<Record<string, unknown>> {
    const response = await this.client.get(`${this.basePath}/dashboard`);
    return response.data as Record<string, unknown>;
  }
}
