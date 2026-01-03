package auth

import (
	"context"
	"fmt"
	"time"

	"go.uber.org/zap"

	"github.com/acgs-project/acgs2-go-sdk/internal/http"
)

// Service provides authentication operations
type Service struct {
	client   *http.Client
	tenantID string
	logger   *zap.Logger

	// Token management
	accessToken  string
	refreshToken string
	tokenExpiry  time.Time
}

// NewService creates a new auth service
func NewService(client *http.Client, tenantID string, logger *zap.Logger) *Service {
	return &Service{
		client:   client,
		tenantID: tenantID,
		logger:   logger,
	}
}

// Login performs user login
func (s *Service) Login(ctx context.Context, username, password string) (*LoginResponse, error) {
	req := &LoginRequest{
		Username: username,
		Password: password,
		TenantID: s.tenantID,
	}

	var resp LoginResponse
	if err := s.client.Do(ctx, "POST", "/auth/login", req, &resp); err != nil {
		s.logger.Error("login failed", zap.Error(err))
		return nil, fmt.Errorf("login failed: %w", err)
	}

	// Store tokens
	s.accessToken = resp.AccessToken
	s.refreshToken = resp.RefreshToken
	s.tokenExpiry = time.Now().Add(time.Duration(resp.ExpiresIn) * time.Second)

	s.logger.Info("login successful", zap.String("user_id", resp.User.ID))
	return &resp, nil
}

// Logout performs user logout
func (s *Service) Logout(ctx context.Context) error {
	if err := s.client.Do(ctx, "POST", "/auth/logout", nil, nil); err != nil {
		s.logger.Error("logout failed", zap.Error(err))
		return fmt.Errorf("logout failed: %w", err)
	}

	// Clear tokens
	s.clearTokens()
	s.logger.Info("logout successful")
	return nil
}

// RefreshToken refreshes the access token
func (s *Service) RefreshToken(ctx context.Context) (*TokenRefreshResponse, error) {
	if s.refreshToken == "" {
		return nil, fmt.Errorf("no refresh token available")
	}

	req := &TokenRefreshRequest{
		RefreshToken: s.refreshToken,
	}

	var resp TokenRefreshResponse
	if err := s.client.Do(ctx, "POST", "/auth/refresh", req, &resp); err != nil {
		s.logger.Error("token refresh failed", zap.Error(err))
		return nil, fmt.Errorf("token refresh failed: %w", err)
	}

	// Update tokens
	s.accessToken = resp.AccessToken
	if resp.RefreshToken != "" {
		s.refreshToken = resp.RefreshToken
	}
	s.tokenExpiry = time.Now().Add(time.Duration(resp.ExpiresIn) * time.Second)

	s.logger.Info("token refreshed")
	return &resp, nil
}

// GetUserInfo retrieves current user information
func (s *Service) GetUserInfo(ctx context.Context) (*UserInfo, error) {
	var user UserInfo
	if err := s.client.Do(ctx, "GET", "/auth/user", nil, &user); err != nil {
		s.logger.Error("failed to get user info", zap.Error(err))
		return nil, fmt.Errorf("failed to get user info: %w", err)
	}

	return &user, nil
}

// UpdateProfile updates user profile
func (s *Service) UpdateProfile(ctx context.Context, updates *ProfileUpdate) (*UserInfo, error) {
	var user UserInfo
	if err := s.client.Do(ctx, "PATCH", "/auth/user", updates, &user); err != nil {
		s.logger.Error("failed to update profile", zap.Error(err))
		return nil, fmt.Errorf("failed to update profile: %w", err)
	}

	s.logger.Info("profile updated", zap.String("user_id", user.ID))
	return &user, nil
}

// ChangePassword changes user password
func (s *Service) ChangePassword(ctx context.Context, currentPassword, newPassword string) error {
	req := &PasswordChange{
		CurrentPassword: currentPassword,
		NewPassword:     newPassword,
	}

	if err := s.client.Do(ctx, "POST", "/auth/change-password", req, nil); err != nil {
		s.logger.Error("password change failed", zap.Error(err))
		return fmt.Errorf("password change failed: %w", err)
	}

	s.logger.Info("password changed")
	return nil
}

// IsAuthenticated checks if the user is authenticated
func (s *Service) IsAuthenticated() bool {
	return s.accessToken != "" && time.Now().Before(s.tokenExpiry)
}

// GetAccessToken returns the current access token
func (s *Service) GetAccessToken() string {
	return s.accessToken
}

// GetTokenExpiry returns the token expiry time
func (s *Service) GetTokenExpiry() time.Time {
	return s.tokenExpiry
}

// ClearTokens clears all stored tokens
func (s *Service) ClearTokens() {
	s.clearTokens()
}

// Health checks the auth service health
func (s *Service) Health(ctx context.Context) (bool, error) {
	var response map[string]interface{}
	if err := s.client.Do(ctx, "GET", "/health/auth", nil, &response); err != nil {
		return false, err
	}

	status, ok := response["status"].(string)
	return ok && status == "healthy", nil
}

// clearTokens clears stored tokens
func (s *Service) clearTokens() {
	s.accessToken = ""
	s.refreshToken = ""
	s.tokenExpiry = time.Time{}
}
