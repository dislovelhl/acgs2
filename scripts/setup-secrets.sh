#!/bin/bash
# ACGS-2 Secure Secrets Setup
# Constitutional Hash: cdd01ef066bc6cf2
#
# This script securely sets up development credentials with:
# - Secure prompting (no echo)
# - Optional Vault integration
# - Encrypted local backup
# - Proper file permissions
#
# Usage:
#   ./scripts/setup-secrets.sh [--vault] [--encrypt]
#
# Options:
#   --vault    Store secrets in HashiCorp Vault
#   --encrypt  Create encrypted backup of .env file

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
ENV_FILE="${PROJECT_ROOT}/.env"
ENV_TEMPLATE="${PROJECT_ROOT}/.env.template"
SECRETS_BACKUP="${PROJECT_ROOT}/.secrets.enc"
VAULT_PATH="secret/acgs2/development"

# Parse arguments
USE_VAULT=false
ENCRYPT_BACKUP=false
for arg in "$@"; do
    case $arg in
        --vault) USE_VAULT=true ;;
        --encrypt) ENCRYPT_BACKUP=true ;;
        -h|--help)
            echo "Usage: $0 [--vault] [--encrypt]"
            echo "  --vault    Store secrets in HashiCorp Vault"
            echo "  --encrypt  Create encrypted backup of .env file"
            exit 0
            ;;
    esac
done

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         ACGS-2 Secure Secrets Setup                         ║"
echo "║         Constitutional Hash: cdd01ef066bc6cf2               ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if template exists
if [[ ! -f "$ENV_TEMPLATE" ]]; then
    echo -e "${RED}Error: .env.template not found at $ENV_TEMPLATE${NC}"
    exit 1
fi

# Check for existing .env
if [[ -f "$ENV_FILE" ]]; then
    echo -e "${YELLOW}⚠️  Existing .env file found.${NC}"
    read -p "Overwrite existing configuration? (y/N): " overwrite
    if [[ ! "$overwrite" =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Keeping existing configuration.${NC}"
        exit 0
    fi
    # Backup existing
    cp "$ENV_FILE" "${ENV_FILE}.backup.$(date +%s)"
    echo -e "${GREEN}Backed up existing .env${NC}"
fi

# Copy template
cp "$ENV_TEMPLATE" "$ENV_FILE"
chmod 600 "$ENV_FILE"  # Restrict permissions

echo ""
echo -e "${BLUE}📝 Enter your credentials (input is hidden for security)${NC}"
echo -e "${YELLOW}Press Enter to skip optional fields${NC}"
echo ""

# Function to securely prompt for secret
prompt_secret() {
    local var_name="$1"
    local prompt_text="$2"
    local required="${3:-false}"
    local validation="${4:-}"

    while true; do
        echo -ne "${CYAN}${prompt_text}${NC}"
        read -s value
        echo ""

        # Skip if empty and optional
        if [[ -z "$value" ]]; then
            if [[ "$required" == "true" ]]; then
                echo -e "${RED}This field is required. Please enter a value.${NC}"
                continue
            else
                return
            fi
        fi

        # Validate format if pattern provided
        if [[ -n "$validation" ]]; then
            if [[ ! "$value" =~ $validation ]]; then
                echo -e "${RED}Invalid format. Please try again.${NC}"
                continue
            fi
        fi

        # Update .env file
        if grep -q "^${var_name}=" "$ENV_FILE"; then
            # Use different sed syntax based on OS
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' "s|^${var_name}=.*|${var_name}=${value}|" "$ENV_FILE"
            else
                sed -i "s|^${var_name}=.*|${var_name}=${value}|" "$ENV_FILE"
            fi
        else
            echo "${var_name}=${value}" >> "$ENV_FILE"
        fi

        break
    done
}

# Function to generate secure random string
generate_random() {
    local length="${1:-32}"
    openssl rand -hex "$length"
}

echo -e "${GREEN}━━━ AI Provider Credentials ━━━${NC}"
echo ""

# Anthropic/Claude
echo -e "${YELLOW}Anthropic Claude Code OAuth Token${NC}"
echo "Get from: https://console.anthropic.com"
prompt_secret "CLAUDE_CODE_OAUTH_TOKEN" "Claude OAuth Token: " "false" "^sk-ant-"

# OpenAI
echo ""
echo -e "${YELLOW}OpenAI API Key${NC}"
echo "Get from: https://platform.openai.com/api-keys"
prompt_secret "OPENAI_API_KEY" "OpenAI API Key: " "false" "^sk-"

# OpenRouter (optional)
echo ""
echo -e "${YELLOW}OpenRouter API Key (optional)${NC}"
echo "Get from: https://openrouter.ai/keys"
prompt_secret "OPENROUTER_API_KEY" "OpenRouter API Key: " "false" "^sk-or-"

# HuggingFace (optional)
echo ""
echo -e "${YELLOW}HuggingFace Token (optional)${NC}"
echo "Get from: https://huggingface.co/settings/tokens"
prompt_secret "HF_TOKEN" "HuggingFace Token: " "false" "^hf_"

echo ""
echo -e "${GREEN}━━━ Security Credentials ━━━${NC}"
echo ""

# Generate JWT Secret automatically
JWT_SECRET=$(generate_random 32)
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s|^JWT_SECRET=.*|JWT_SECRET=${JWT_SECRET}|" "$ENV_FILE"
else
    sed -i "s|^JWT_SECRET=.*|JWT_SECRET=${JWT_SECRET}|" "$ENV_FILE"
fi
echo -e "${GREEN}✓ Generated JWT_SECRET (64 hex chars)${NC}"

# Generate Internal API Key automatically
API_KEY=$(generate_random 32)
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s|^API_KEY_INTERNAL=.*|API_KEY_INTERNAL=${API_KEY}|" "$ENV_FILE"
else
    sed -i "s|^API_KEY_INTERNAL=.*|API_KEY_INTERNAL=${API_KEY}|" "$ENV_FILE"
fi
echo -e "${GREEN}✓ Generated API_KEY_INTERNAL (64 hex chars)${NC}"

# Vault integration
if [[ "$USE_VAULT" == "true" ]]; then
    echo ""
    echo -e "${GREEN}━━━ Vault Integration ━━━${NC}"

    if ! command -v vault &> /dev/null; then
        echo -e "${RED}Error: vault CLI not found. Install from https://www.vaultproject.io/downloads${NC}"
    else
        if [[ -z "$VAULT_TOKEN" ]]; then
            prompt_secret "VAULT_TOKEN" "Vault Token: " "false"
        fi

        if [[ -n "${VAULT_TOKEN:-}" ]]; then
            echo -e "${BLUE}Storing secrets in Vault at ${VAULT_PATH}...${NC}"

            # Extract secrets to store in Vault
            CLAUDE_TOKEN=$(grep "^CLAUDE_CODE_OAUTH_TOKEN=" "$ENV_FILE" | cut -d'=' -f2-)
            OPENAI_KEY=$(grep "^OPENAI_API_KEY=" "$ENV_FILE" | cut -d'=' -f2-)

            vault kv put "$VAULT_PATH" \
                claude_oauth_token="${CLAUDE_TOKEN:-}" \
                openai_api_key="${OPENAI_KEY:-}" \
                jwt_secret="${JWT_SECRET}" \
                api_key_internal="${API_KEY}" \
                2>/dev/null && \
                echo -e "${GREEN}✓ Secrets stored in Vault${NC}" || \
                echo -e "${YELLOW}⚠️  Could not store secrets in Vault (check connection/permissions)${NC}"
        fi
    fi
fi

# Encrypted backup
if [[ "$ENCRYPT_BACKUP" == "true" ]]; then
    echo ""
    echo -e "${GREEN}━━━ Encrypted Backup ━━━${NC}"

    if command -v gpg &> /dev/null; then
        echo -ne "${CYAN}Enter passphrase for encrypted backup: ${NC}"
        read -s passphrase
        echo ""

        echo "$passphrase" | gpg --batch --yes --passphrase-fd 0 -c -o "$SECRETS_BACKUP" "$ENV_FILE" 2>/dev/null
        echo -e "${GREEN}✓ Encrypted backup saved to ${SECRETS_BACKUP}${NC}"
        echo -e "${YELLOW}  To restore: gpg -d ${SECRETS_BACKUP} > .env${NC}"
    else
        echo -e "${YELLOW}⚠️  gpg not found, skipping encrypted backup${NC}"
    fi
fi

# Final permissions check
chmod 600 "$ENV_FILE"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗"
echo -e "║  ✅ Secrets setup complete!                                   ║"
echo -e "╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Configuration saved to: ${ENV_FILE}${NC}"
echo -e "${BLUE}File permissions: 600 (owner read/write only)${NC}"
echo ""
echo -e "${YELLOW}Security Reminders:${NC}"
echo "  1. Never commit .env to version control"
echo "  2. Rotate credentials every 90 days"
echo "  3. Use Vault for production: ./scripts/setup-secrets.sh --vault"
echo "  4. Backup encrypted: ./scripts/setup-secrets.sh --encrypt"
echo ""
echo -e "${GREEN}To load configuration:${NC}"
echo "  source .env"
echo "  # or"
echo "  export \$(grep -v '^#' .env | xargs)"
echo ""

# Verify .gitignore
if ! grep -q "^\.env$" "${PROJECT_ROOT}/.gitignore" 2>/dev/null; then
    echo -e "${RED}⚠️  WARNING: .env may not be in .gitignore!${NC}"
    echo -e "${YELLOW}Add this line to .gitignore:${NC}"
    echo "  .env"
fi
