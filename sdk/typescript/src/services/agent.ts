/**
 * ACGS-2 Agent Service
 * Constitutional Hash: cdd01ef066bc6cf2
 */

import EventEmitter from 'eventemitter3';
import { ACGS2Client } from '../client';
import {
  CONSTITUTIONAL_HASH,
  AgentMessage,
  AgentMessageSchema,
  MessageType,
  Priority,
  SendMessageRequest,
  PaginationParams,
  PaginatedResponse,
  ACGS2Event,
  EventHandler,
} from '../types';
import { generateUUID, nowISO, ValidationError, Logger, createLogger, silentLogger } from '../utils';

// =============================================================================
// Agent Types
// =============================================================================

export interface AgentInfo {
  id: string;
  name: string;
  type: string;
  status: 'active' | 'inactive' | 'suspended';
  capabilities: string[];
  metadata: Record<string, string>;
  lastSeen: string;
  constitutionalHash: string;
}

export interface AgentRegistration {
  name: string;
  type: string;
  capabilities: string[];
  metadata?: Record<string, string>;
}

// =============================================================================
// Agent Service
// =============================================================================

export class AgentService {
  private readonly basePath = '/api/v1/agents';
  private readonly eventEmitter: EventEmitter;
  private readonly logger: Logger;
  private agentId?: string;
  private websocket?: WebSocket;
  private reconnectAttempts = 0;
  private readonly maxReconnectAttempts = 5;

  constructor(
    private readonly client: ACGS2Client,
    options?: { logger?: Logger }
  ) {
    this.eventEmitter = new EventEmitter();
    this.logger = options?.logger ?? silentLogger;
  }

  // ===========================================================================
  // Agent Registration
  // ===========================================================================

  /**
   * Registers an agent with the ACGS-2 system
   */
  async register(registration: AgentRegistration): Promise<AgentInfo> {
    const response = await this.client.post<AgentInfo>(`${this.basePath}/register`, {
      ...registration,
      constitutionalHash: CONSTITUTIONAL_HASH,
    });

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to register agent');
    }

    this.agentId = response.data.id;
    this.logger.info(`Agent registered: ${this.agentId}`);
    return response.data;
  }

  /**
   * Unregisters the current agent
   */
  async unregister(): Promise<void> {
    if (!this.agentId) {
      throw new ValidationError('Agent not registered');
    }

    await this.client.delete(`${this.basePath}/${this.agentId}`);
    this.logger.info(`Agent unregistered: ${this.agentId}`);
    this.agentId = undefined;
  }

  /**
   * Gets the current agent's ID
   */
  getAgentId(): string | undefined {
    return this.agentId;
  }

  /**
   * Sets the agent ID (for existing agents)
   */
  setAgentId(agentId: string): void {
    this.agentId = agentId;
  }

  // ===========================================================================
  // Agent Information
  // ===========================================================================

  /**
   * Gets agent information by ID
   */
  async get(agentId: string): Promise<AgentInfo> {
    const response = await this.client.get<AgentInfo>(`${this.basePath}/${agentId}`);

    if (!response.success || !response.data) {
      throw new ValidationError(`Agent not found: ${agentId}`);
    }

    return response.data;
  }

  /**
   * Lists all registered agents
   */
  async list(params?: PaginationParams & {
    type?: string;
    status?: 'active' | 'inactive' | 'suspended';
  }): Promise<PaginatedResponse<AgentInfo>> {
    const response = await this.client.get<PaginatedResponse<AgentInfo>>(this.basePath, params);

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to list agents');
    }

    return response.data;
  }

  /**
   * Updates agent metadata
   */
  async updateMetadata(metadata: Record<string, string>): Promise<AgentInfo> {
    if (!this.agentId) {
      throw new ValidationError('Agent not registered');
    }

    const response = await this.client.patch<AgentInfo>(`${this.basePath}/${this.agentId}`, {
      metadata,
    });

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to update agent metadata');
    }

    return response.data;
  }

  /**
   * Sends a heartbeat to keep agent active
   */
  async heartbeat(): Promise<void> {
    if (!this.agentId) {
      throw new ValidationError('Agent not registered');
    }

    await this.client.post(`${this.basePath}/${this.agentId}/heartbeat`, {
      timestamp: nowISO(),
      constitutionalHash: CONSTITUTIONAL_HASH,
    });
  }

  // ===========================================================================
  // Messaging
  // ===========================================================================

  /**
   * Sends a message to another agent or broadcast
   */
  async sendMessage(request: SendMessageRequest): Promise<AgentMessage> {
    if (!this.agentId) {
      throw new ValidationError('Agent not registered');
    }

    const message: Omit<AgentMessage, 'id'> = {
      type: request.type,
      priority: request.priority ?? Priority.NORMAL,
      sourceAgentId: this.agentId,
      targetAgentId: request.targetAgentId,
      payload: request.payload,
      timestamp: nowISO(),
      correlationId: request.correlationId,
      constitutionalHash: CONSTITUTIONAL_HASH,
      metadata: request.metadata,
    };

    const response = await this.client.post<AgentMessage>(
      `${this.basePath}/${this.agentId}/messages`,
      message
    );

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to send message');
    }

    return this.validateMessage(response.data);
  }

  /**
   * Sends a command to an agent
   */
  async sendCommand(
    targetAgentId: string,
    command: string,
    params?: Record<string, unknown>,
    options?: { priority?: Priority; correlationId?: string }
  ): Promise<AgentMessage> {
    return this.sendMessage({
      type: MessageType.COMMAND,
      priority: options?.priority ?? Priority.NORMAL,
      targetAgentId,
      payload: { command, params },
      correlationId: options?.correlationId,
    });
  }

  /**
   * Sends a query to an agent
   */
  async sendQuery(
    targetAgentId: string,
    query: string,
    params?: Record<string, unknown>,
    options?: { priority?: Priority; correlationId?: string }
  ): Promise<AgentMessage> {
    return this.sendMessage({
      type: MessageType.QUERY,
      priority: options?.priority ?? Priority.NORMAL,
      targetAgentId,
      payload: { query, params },
      correlationId: options?.correlationId,
    });
  }

  /**
   * Broadcasts an event to all agents
   */
  async broadcastEvent(
    eventType: string,
    data: Record<string, unknown>,
    options?: { priority?: Priority }
  ): Promise<AgentMessage> {
    return this.sendMessage({
      type: MessageType.EVENT,
      priority: options?.priority ?? Priority.NORMAL,
      payload: { eventType, data },
    });
  }

  /**
   * Gets messages for the current agent
   */
  async getMessages(params?: PaginationParams & {
    type?: MessageType;
    since?: string;
    unreadOnly?: boolean;
  }): Promise<PaginatedResponse<AgentMessage>> {
    if (!this.agentId) {
      throw new ValidationError('Agent not registered');
    }

    const response = await this.client.get<PaginatedResponse<AgentMessage>>(
      `${this.basePath}/${this.agentId}/messages`,
      params
    );

    if (!response.success || !response.data) {
      throw new ValidationError('Failed to get messages');
    }

    // Validate each message
    response.data.data = response.data.data.map((msg) => this.validateMessage(msg));
    return response.data;
  }

  /**
   * Acknowledges receipt of a message
   */
  async acknowledgeMessage(messageId: string): Promise<void> {
    if (!this.agentId) {
      throw new ValidationError('Agent not registered');
    }

    await this.client.post(`${this.basePath}/${this.agentId}/messages/${messageId}/ack`);
  }

  // ===========================================================================
  // Real-time Subscriptions
  // ===========================================================================

  /**
   * Subscribes to real-time messages via WebSocket
   */
  async subscribe(wsUrl: string): Promise<void> {
    if (this.websocket) {
      this.websocket.close();
    }

    return new Promise((resolve, reject) => {
      const url = `${wsUrl}?agentId=${this.agentId}&hash=${CONSTITUTIONAL_HASH}`;
      this.websocket = new WebSocket(url);

      this.websocket.onopen = () => {
        this.logger.info('WebSocket connected');
        this.reconnectAttempts = 0;
        resolve();
      };

      this.websocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const message = this.validateMessage(data);
          this.eventEmitter.emit('message', message);
          this.eventEmitter.emit(`message:${message.type}`, message);
        } catch (error) {
          this.logger.error('Failed to parse WebSocket message:', error);
        }
      };

      this.websocket.onerror = (error) => {
        this.logger.error('WebSocket error:', error);
        this.eventEmitter.emit('error', error);
      };

      this.websocket.onclose = () => {
        this.logger.info('WebSocket disconnected');
        this.eventEmitter.emit('disconnected');
        this.attemptReconnect(wsUrl);
      };
    });
  }

  /**
   * Unsubscribes from real-time messages
   */
  unsubscribe(): void {
    if (this.websocket) {
      this.websocket.close();
      this.websocket = undefined;
    }
    this.reconnectAttempts = this.maxReconnectAttempts; // Prevent reconnection
  }

  /**
   * Registers a message handler
   */
  onMessage(handler: EventHandler<AgentMessage>): () => void {
    this.eventEmitter.on('message', handler);
    return () => this.eventEmitter.off('message', handler);
  }

  /**
   * Registers a handler for specific message types
   */
  onMessageType(type: MessageType, handler: EventHandler<AgentMessage>): () => void {
    this.eventEmitter.on(`message:${type}`, handler);
    return () => this.eventEmitter.off(`message:${type}`, handler);
  }

  /**
   * Registers a handler for connection errors
   */
  onError(handler: (error: Error) => void): () => void {
    this.eventEmitter.on('error', handler);
    return () => this.eventEmitter.off('error', handler);
  }

  /**
   * Registers a handler for disconnection
   */
  onDisconnected(handler: () => void): () => void {
    this.eventEmitter.on('disconnected', handler);
    return () => this.eventEmitter.off('disconnected', handler);
  }

  private async attemptReconnect(wsUrl: string): Promise<void> {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      this.logger.error('Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
    this.logger.info(`Attempting reconnection in ${delay}ms (attempt ${this.reconnectAttempts})`);

    await new Promise((resolve) => setTimeout(resolve, delay));

    try {
      await this.subscribe(wsUrl);
    } catch (error) {
      this.logger.error('Reconnection failed:', error);
    }
  }

  // ===========================================================================
  // Helpers
  // ===========================================================================

  private validateMessage(data: unknown): AgentMessage {
    const result = AgentMessageSchema.safeParse(data);
    if (!result.success) {
      throw new ValidationError('Invalid message data', {
        validation: result.error.errors.map((e) => e.message),
      });
    }
    return result.data;
  }
}
