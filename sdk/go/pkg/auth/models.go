package auth

import "time"

// LoginRequest represents a login request
type LoginRequest struct {
	Username string `json:"username"`
	Password string `json:"password"`
	TenantID string `json:"tenant_id,omitempty"`
}

// LoginResponse represents a login response
type LoginResponse struct {
	AccessToken  string    `json:"access_token"`
	RefreshToken string    `json:"refresh_token"`
	TokenType    string    `json:"token_type"`
	ExpiresIn    int       `json:"expires_in"`
	User         UserInfo  `json:"user"`
}

// TokenRefreshRequest represents a token refresh request
type TokenRefreshRequest struct {
	RefreshToken string `json:"refresh_token"`
}

// TokenRefreshResponse represents a token refresh response
type TokenRefreshResponse struct {
	AccessToken  string `json:"access_token"`
	RefreshToken string `json:"refresh_token,omitempty"`
	TokenType    string `json:"token_type"`
	ExpiresIn    int    `json:"expires_in"`
}

// UserInfo represents user information
type UserInfo struct {
	ID            string    `json:"id"`
	Username      string    `json:"username"`
	Email         string    `json:"email"`
	FirstName     string    `json:"first_name,omitempty"`
	LastName      string    `json:"last_name,omitempty"`
	Roles         []string  `json:"roles"`
	Permissions   []string  `json:"permissions"`
	TenantID      string    `json:"tenant_id"`
	LastLogin     *time.Time `json:"last_login,omitempty"`
	IsActive      bool      `json:"is_active"`
	CreatedAt     time.Time `json:"created_at"`
	UpdatedAt     time.Time `json:"updated_at"`
}

// ProfileUpdate represents profile update data
type ProfileUpdate struct {
	FirstName *string `json:"first_name,omitempty"`
	LastName  *string `json:"last_name,omitempty"`
	Email     *string `json:"email,omitempty"`
}

// PasswordChange represents a password change request
type PasswordChange struct {
	CurrentPassword string `json:"current_password"`
	NewPassword     string `json:"new_password"`
}

// AuthState represents the current authentication state
type AuthState struct {
	IsAuthenticated bool       `json:"is_authenticated"`
	User            *UserInfo  `json:"user,omitempty"`
	TokenExpiry     *time.Time `json:"token_expiry,omitempty"`
}
