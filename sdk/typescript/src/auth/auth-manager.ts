/**
 * ACGS-2 Authentication Manager
 * Constitutional Hash: cdd01ef066bc6cf2
 */

import { EventEmitter } from 'eventemitter3';
import { z } from 'zod';
import { AxiosInstance } from 'axios';
import { TenantContext } from '../core/tenant';
import { JWTManager } from './jwt-manager';

// Auth schemas
export const LoginRequestSchema = z.object({
  username: z.string().min(1),
  password: z.string().min(1),
  tenantId: z.string().optional(),
});

export const LoginResponseSchema = z.object({
  accessToken: z.string(),
  refreshToken: z.string(),
  tokenType: z.string().default('Bearer'),
  expiresIn: z.number(),
  user: z.object({
    id: z.string(),
    username: z.string(),
    email: z.string(),
    roles: z.array(z.string()),
    permissions: z.array(z.string()),
  }),
});

export const TokenRefreshRequestSchema = z.object({
  refreshToken: z.string(),
});

export const TokenRefreshResponseSchema = z.object({
  accessToken: z.string(),
  refreshToken: z.string().optional(),
  tokenType: z.string().default('Bearer'),
  expiresIn: z.number(),
});

export const UserInfoSchema = z.object({
  id: z.string(),
  username: z.string(),
  email: z.string(),
  firstName: z.string().optional(),
  lastName: z.string().optional(),
  roles: z.array(z.string()),
  permissions: z.array(z.string()),
  tenantId: z.string(),
  lastLogin: z.date().optional(),
  isActive: z.boolean(),
});

export type LoginRequest = z.infer<typeof LoginRequestSchema>;
export type LoginResponse = z.infer<typeof LoginResponseSchema>;
export type TokenRefreshRequest = z.infer<typeof TokenRefreshRequestSchema>;
export type TokenRefreshResponse = z.infer<typeof TokenRefreshResponseSchema>;
export type UserInfo = z.infer<typeof UserInfoSchema>;

// Auth state
export interface AuthState {
  isAuthenticated: boolean;
  user?: UserInfo;
  accessToken?: string;
  refreshToken?: string;
  expiresAt?: Date;
}

// Auth events
export interface AuthEvents {
  authenticated: (userId: string) => void;
  deauthenticated: () => void;
  tokenRefreshed: (expiresAt: Date) => void;
  tokenExpired: () => void;
  loginFailed: (error: Error) => void;
}

/**
 * Authentication Manager
 * Handles user authentication, token management, and session lifecycle
 */
export class AuthManager extends EventEmitter<AuthEvents> {
  private jwtManager: JWTManager;
  private authState: AuthState = { isAuthenticated: false };
  private refreshTimer?: NodeJS.Timeout;
  private isRefreshing = false;

  constructor(
    private httpClient: AxiosInstance,
    private tenantContext: TenantContext
  ) {
    super();
    this.jwtManager = new JWTManager();
    this.setupAutoRefresh();
  }

  /**
   * Initialize auth manager
   */
  async initialize(): Promise<void> {
    // Check for existing tokens
    const storedTokens = this.getStoredTokens();
    if (storedTokens) {
      try {
        await this.validateAndSetTokens(storedTokens.accessToken, storedTokens.refreshToken);
      } catch (error) {
        // Tokens are invalid, clear them
        this.clearStoredTokens();
      }
    }
  }

  /**
   * Switch tenant context
   */
  async switchTenant(newContext: TenantContext): Promise<void> {
    this.tenantContext = newContext;
    // If authenticated, validate that user has access to new tenant
    if (this.authState.isAuthenticated && this.authState.user) {
      if (this.authState.user.tenantId !== newContext.tenantId) {
        // User doesn't have access to new tenant, deauthenticate
        await this.logout();
      }
    }
  }

  /**
   * Login user
   */
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    try {
      const response = await this.httpClient.post<LoginResponse>('/auth/login', {
        ...credentials,
        tenantId: credentials.tenantId || this.tenantContext.tenantId,
      });

      const loginResponse = LoginResponseSchema.parse(response.data);

      await this.validateAndSetTokens(loginResponse.accessToken, loginResponse.refreshToken);

      this.emit('authenticated', loginResponse.user.id);

      return loginResponse;
    } catch (error) {
      this.emit('loginFailed', error as Error);
      throw error;
    }
  }

  /**
   * Logout user
   */
  async logout(): Promise<void> {
    try {
      if (this.authState.accessToken) {
        await this.httpClient.post('/auth/logout');
      }
    } catch (error) {
      // Ignore logout errors
    } finally {
      this.clearAuthState();
      this.clearStoredTokens();
      this.clearRefreshTimer();
      this.emit('deauthenticated');
    }
  }

  /**
   * Refresh access token
   */
  async refreshToken(): Promise<TokenRefreshResponse> {
    if (!this.authState.refreshToken || this.isRefreshing) {
      throw new Error('No refresh token available or refresh in progress');
    }

    this.isRefreshing = true;

    try {
      const response = await this.httpClient.post<TokenRefreshResponse>('/auth/refresh', {
        refreshToken: this.authState.refreshToken,
      });

      const refreshResponse = TokenRefreshResponseSchema.parse(response.data);

      await this.validateAndSetTokens(
        refreshResponse.accessToken,
        refreshResponse.refreshToken || this.authState.refreshToken
      );

      this.emit('tokenRefreshed', this.authState.expiresAt!);

      return refreshResponse;
    } finally {
      this.isRefreshing = false;
    }
  }

  /**
   * Get current user info
   */
  async getUserInfo(): Promise<UserInfo> {
    this.ensureAuthenticated();

    const response = await this.httpClient.get<UserInfo>('/auth/user');
    return UserInfoSchema.parse(response.data);
  }

  /**
   * Update user profile
   */
  async updateProfile(updates: Partial<Pick<UserInfo, 'firstName' | 'lastName' | 'email'>>): Promise<UserInfo> {
    this.ensureAuthenticated();

    const response = await this.httpClient.patch<UserInfo>('/auth/user', updates);
    const updatedUser = UserInfoSchema.parse(response.data);

    // Update local state
    if (this.authState.user) {
      this.authState.user = { ...this.authState.user, ...updatedUser };
      this.tenantContext.setUserId(updatedUser.id);
    }

    return updatedUser;
  }

  /**
   * Change password
   */
  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    this.ensureAuthenticated();

    await this.httpClient.post('/auth/change-password', {
      currentPassword,
      newPassword,
    });
  }

  /**
   * Get current auth state
   */
  getAuthState(): AuthState {
    return { ...this.authState };
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return this.authState.isAuthenticated &&
           this.authState.expiresAt &&
           this.authState.expiresAt > new Date();
  }

  /**
   * Get current user
   */
  getCurrentUser(): UserInfo | undefined {
    return this.authState.user;
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<boolean> {
    try {
      await this.httpClient.get('/auth/health');
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Get metrics
   */
  getMetrics(): Record<string, any> {
    return {
      isAuthenticated: this.isAuthenticated(),
      userId: this.authState.user?.id,
      tenantId: this.authState.user?.tenantId,
      expiresAt: this.authState.expiresAt?.toISOString(),
      isRefreshing: this.isRefreshing,
    };
  }

  /**
   * Dispose resources
   */
  dispose(): void {
    this.clearRefreshTimer();
    this.removeAllListeners();
  }

  /**
   * Validate tokens and set auth state
   */
  private async validateAndSetTokens(accessToken: string, refreshToken: string): Promise<void> {
    // Validate access token
    const payload = this.jwtManager.verifyToken(accessToken);
    if (!payload) {
      throw new Error('Invalid access token');
    }

    // Get user info from token or API
    let userInfo: UserInfo;
    try {
      userInfo = await this.getUserInfo();
    } catch {
      // If API call fails, extract from token (less secure but fallback)
      userInfo = {
        id: payload.sub,
        username: payload.username || '',
        email: payload.email || '',
        roles: payload.roles || [],
        permissions: payload.permissions || [],
        tenantId: payload.tenantId || this.tenantContext.tenantId,
        isActive: true,
      };
    }

    // Set auth state
    this.authState = {
      isAuthenticated: true,
      user: userInfo,
      accessToken,
      refreshToken,
      expiresAt: new Date(payload.exp * 1000),
    };

    // Update tenant context
    this.tenantContext.setUserId(userInfo.id);
    this.tenantContext.setPermissions(userInfo.permissions);

    // Store tokens
    this.storeTokens(accessToken, refreshToken);

    // Setup auto-refresh
    this.setupAutoRefresh();
  }

  /**
   * Clear auth state
   */
  private clearAuthState(): void {
    this.authState = { isAuthenticated: false };
    this.tenantContext.setUserId(undefined);
    this.tenantContext.setPermissions([]);
  }

  /**
   * Ensure user is authenticated
   */
  private ensureAuthenticated(): void {
    if (!this.isAuthenticated()) {
      throw new Error('User not authenticated');
    }
  }

  /**
   * Setup automatic token refresh
   */
  private setupAutoRefresh(): void {
    this.clearRefreshTimer();

    if (this.authState.expiresAt) {
      // Refresh 5 minutes before expiry
      const refreshTime = this.authState.expiresAt.getTime() - Date.now() - (5 * 60 * 1000);

      if (refreshTime > 0) {
        this.refreshTimer = setTimeout(async () => {
          try {
            await this.refreshToken();
          } catch (error) {
            this.emit('tokenExpired');
            await this.logout();
          }
        }, refreshTime);
      } else {
        // Token is already expired or will expire soon
        this.emit('tokenExpired');
      }
    }
  }

  /**
   * Clear refresh timer
   */
  private clearRefreshTimer(): void {
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
      this.refreshTimer = undefined;
    }
  }

  /**
   * Store tokens in local storage (client-side only)
   */
  private storeTokens(accessToken: string, refreshToken: string): void {
    if (typeof window !== 'undefined') {
      localStorage.setItem(`acgs2_auth_${this.tenantContext.tenantId}`, JSON.stringify({
        accessToken,
        refreshToken,
        expiresAt: this.authState.expiresAt?.toISOString(),
      }));
    }
  }

  /**
   * Get stored tokens
   */
  private getStoredTokens(): { accessToken: string; refreshToken: string } | null {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(`acgs2_auth_${this.tenantContext.tenantId}`);
      if (stored) {
        try {
          return JSON.parse(stored);
        } catch {
          return null;
        }
      }
    }
    return null;
  }

  /**
   * Clear stored tokens
   */
  private clearStoredTokens(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem(`acgs2_auth_${this.tenantContext.tenantId}`);
    }
  }
}
