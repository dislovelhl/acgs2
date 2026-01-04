#!/bin/bash

# ACGS-2 Production Secrets Generator
# Constitutional Hash: cdd01ef066bc6cf2
#
# This script generates cryptographically secure secrets for production deployment.
# Run this script to generate values for your .env.production file.

set -e

echo "🔐 ACGS-2 Production Secrets Generator"
echo "====================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to generate a secure random string
generate_secret() {
    local length=${1:-32}
    openssl rand -hex $length
}

# Function to generate a secure password
generate_password() {
    local length=${1:-16}
    openssl rand -base64 $length | tr -d "=+/" | cut -c1-$length
}

echo -e "${BLUE}Generating production secrets...${NC}"
echo ""

# JWT Secrets
echo -e "${GREEN}1. JWT Configuration${NC}"
echo "# JWT_SECRET (64 characters - 256 bits)"
echo -n "JWT_SECRET="
generate_secret 32
echo ""

echo "# JWT_PRIVATE_KEY (RSA Private Key for advanced JWT)"
echo "# Run: openssl genrsa -out jwt-private.pem 2048"
echo "# Then: openssl rsa -in jwt-private.pem -pubout -out jwt-public.pem"
echo "# JWT_PRIVATE_KEY=\"$(cat jwt-private.pem)\""
echo "# JWT_PUBLIC_KEY=\"$(cat jwt-public.pem)\""
echo ""

# API Keys
echo -e "${GREEN}2. API Keys${NC}"
echo "# API_KEY_INTERNAL (32 characters)"
echo -n "API_KEY_INTERNAL="
generate_secret 32
echo ""

# Blockchain Keys
echo -e "${GREEN}3. Blockchain Configuration${NC}"
echo "# BLOCKCHAIN_PRIVATE_KEY (Ethereum private key - keep ultra-secure!)"
echo "# Generate with: openssl rand -hex 32"
echo -n "BLOCKCHAIN_PRIVATE_KEY="
generate_secret 32
echo ""

# Audit Encryption
echo -e "${GREEN}4. Audit Encryption${NC}"
echo "# AUDIT_ENCRYPTION_KEY (32 characters - AES-256)"
echo -n "AUDIT_ENCRYPTION_KEY="
generate_secret 32
echo ""

# Database Passwords
echo -e "${GREEN}5. Database Credentials${NC}"
echo "# Database passwords (16 characters each)"
echo -n "DB_USER_PASSWORD="
generate_password 16
echo ""

echo -n "REDIS_PASSWORD="
generate_password 16
echo ""

# Kafka SASL
echo -e "${GREEN}6. Kafka SASL Credentials${NC}"
echo "# Kafka SASL credentials"
echo -n "KAFKA_SASL_USERNAME="
echo "acgs2-prod-user"  # You should customize this
echo ""

echo -n "KAFKA_SASL_PASSWORD="
generate_password 20
echo ""

# Vault Token
echo -e "${GREEN}7. Vault Configuration${NC}"
echo "# Vault root token (generate during Vault setup)"
echo "# VAULT_TOKEN=your-vault-root-token-here"
echo ""

# AWS Credentials
echo -e "${GREEN}8. AWS Credentials${NC}"
echo "# AWS credentials (obtain from AWS IAM)"
echo "# AWS_ACCESS_KEY_ID=your-aws-access-key-id"
echo "# AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key"
echo ""

# OAuth2 Client Secrets
echo -e "${GREEN}9. OAuth2 Client Secrets${NC}"
echo "# OAuth2 client secrets (obtain from providers)"
echo "# OAUTH2_GOOGLE_CLIENT_SECRET=your-google-client-secret"
echo "# OAUTH2_GITHUB_CLIENT_SECRET=your-github-client-secret"
echo ""

echo -e "${YELLOW}⚠️  Security Recommendations:${NC}"
echo "1. Store these secrets in a secure secret management system (Vault, AWS Secrets Manager, etc.)"
echo "2. Never commit secrets to version control"
echo "3. Rotate secrets regularly (every 90 days)"
echo "4. Use different secrets for each environment"
echo "5. Backup encrypted versions of critical secrets"
echo ""

echo -e "${YELLOW}📝 Next Steps:${NC}"
echo "1. Copy the generated values above to your .env.production file"
echo "2. Set up JWT key pairs using the OpenSSL commands shown"
echo "3. Configure OAuth2 applications in respective providers"
echo "4. Set up Vault and generate root token"
echo "5. Configure AWS IAM user with minimal required permissions"
echo ""

echo -e "${RED}🚨 Critical Security Notes:${NC}"
echo "• JWT_SECRET and BLOCKCHAIN_PRIVATE_KEY are CRITICAL - compromise means total system breach"
echo "• Store blockchain private keys in hardware security modules (HSM) if possible"
echo "• Enable audit logging BEFORE going to production"
echo "• Test secret rotation procedures before production deployment"
echo ""

echo -e "${GREEN}✅ Secrets generation complete!${NC}"
echo "Copy the values above to your production environment configuration."
