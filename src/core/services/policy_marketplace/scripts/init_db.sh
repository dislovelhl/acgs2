#!/bin/bash
# Policy Marketplace Database Initialization Script
# Constitutional Hash: cdd01ef066bc6cf2
# Version: 1.0.0
#
# This script initializes the PostgreSQL database for the Policy Marketplace service.
# It creates the database and user if they don't exist, and grants appropriate privileges.
#
# Usage:
#   ./init_db.sh                  # Use defaults or environment variables
#   ./init_db.sh --check          # Check if database is accessible
#   ./init_db.sh --help           # Show help
#
# Environment Variables:
#   POSTGRES_HOST      - PostgreSQL host (default: localhost)
#   POSTGRES_PORT      - PostgreSQL port (default: 5432)
#   POSTGRES_USER      - Admin user (default: postgres)
#   POSTGRES_PASSWORD  - Admin password (default: from env or prompt)
#   MARKETPLACE_DB     - Target database name (default: acgs2_marketplace)
#   MARKETPLACE_USER   - Application user (default: acgs2_user)
#   MARKETPLACE_PASS   - Application password (default: acgs2_pass)

set -e

# =============================================================================
# Configuration
# =============================================================================

POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"
MARKETPLACE_DB="${MARKETPLACE_DB:-acgs2_marketplace}"
MARKETPLACE_USER="${MARKETPLACE_USER:-acgs2_user}"
MARKETPLACE_PASS="${MARKETPLACE_PASS:-acgs2_pass}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}=================================================================${NC}"
    echo -e "${BLUE}  Policy Marketplace Database Initialization${NC}"
    echo -e "${BLUE}  Constitutional Hash: cdd01ef066bc6cf2${NC}"
    echo -e "${BLUE}=================================================================${NC}"
    echo ""
}

success() {
    echo -e "  ${GREEN}✓${NC} $1"
}

warn() {
    echo -e "  ${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "  ${RED}✗${NC} $1"
}

info() {
    echo -e "  ${BLUE}ℹ${NC} $1"
}

show_help() {
    cat << EOF
Policy Marketplace Database Initialization Script

Usage: ./init_db.sh [OPTIONS]

Options:
  --help, -h       Show this help message
  --check          Check if database is accessible (no changes)
  --force          Drop and recreate database if exists
  --skip-user      Skip user creation (use existing user)
  --verbose        Show SQL commands being executed

Environment Variables:
  POSTGRES_HOST      PostgreSQL host (default: localhost)
  POSTGRES_PORT      PostgreSQL port (default: 5432)
  POSTGRES_USER      Admin user for creating database (default: postgres)
  POSTGRES_PASSWORD  Admin password (will prompt if not set)
  MARKETPLACE_DB     Target database name (default: acgs2_marketplace)
  MARKETPLACE_USER   Application user (default: acgs2_user)
  MARKETPLACE_PASS   Application password (default: acgs2_pass)

Examples:
  # Initialize with defaults
  ./init_db.sh

  # Check database connectivity
  ./init_db.sh --check

  # Use custom settings
  POSTGRES_HOST=db.example.com MARKETPLACE_DB=my_marketplace ./init_db.sh

  # Force recreate database
  ./init_db.sh --force

EOF
}

# Build psql connection string
get_psql_cmd() {
    local db="${1:-postgres}"
    local cmd="psql"

    if [[ -n "$POSTGRES_PASSWORD" ]]; then
        cmd="PGPASSWORD='$POSTGRES_PASSWORD' psql"
    fi

    echo "$cmd -h '$POSTGRES_HOST' -p '$POSTGRES_PORT' -U '$POSTGRES_USER' -d '$db'"
}

# Execute psql command
exec_psql() {
    local db="${1:-postgres}"
    local sql="$2"
    local quiet="${3:-false}"

    local cmd
    if [[ -n "$POSTGRES_PASSWORD" ]]; then
        if [[ "$quiet" == "true" ]]; then
            PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$db" -t -c "$sql" 2>/dev/null
        else
            PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$db" -c "$sql"
        fi
    else
        if [[ "$quiet" == "true" ]]; then
            psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$db" -t -c "$sql" 2>/dev/null
        else
            psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$db" -c "$sql"
        fi
    fi
}

# =============================================================================
# Check Functions
# =============================================================================

check_postgres_connection() {
    info "Checking PostgreSQL connection..."

    if exec_psql "postgres" "SELECT 1;" true > /dev/null 2>&1; then
        success "PostgreSQL is accessible at $POSTGRES_HOST:$POSTGRES_PORT"
        return 0
    else
        error "Cannot connect to PostgreSQL at $POSTGRES_HOST:$POSTGRES_PORT"
        echo ""
        echo "  Troubleshooting:"
        echo "    1. Ensure PostgreSQL is running"
        echo "    2. Check POSTGRES_HOST and POSTGRES_PORT settings"
        echo "    3. Verify POSTGRES_USER and POSTGRES_PASSWORD are correct"
        echo "    4. If using Docker: docker-compose -f docker-compose.dev.yml up -d postgres"
        return 1
    fi
}

check_database_exists() {
    local result
    result=$(exec_psql "postgres" "SELECT 1 FROM pg_database WHERE datname = '$MARKETPLACE_DB';" true 2>/dev/null | tr -d '[:space:]')
    [[ "$result" == "1" ]]
}

check_user_exists() {
    local result
    result=$(exec_psql "postgres" "SELECT 1 FROM pg_roles WHERE rolname = '$MARKETPLACE_USER';" true 2>/dev/null | tr -d '[:space:]')
    [[ "$result" == "1" ]]
}

# =============================================================================
# Database Operations
# =============================================================================

create_user() {
    if check_user_exists; then
        info "User '$MARKETPLACE_USER' already exists"

        # Update password for existing user
        info "Updating password for user '$MARKETPLACE_USER'..."
        exec_psql "postgres" "ALTER USER $MARKETPLACE_USER WITH PASSWORD '$MARKETPLACE_PASS';" > /dev/null 2>&1
        success "Password updated for user '$MARKETPLACE_USER'"
    else
        info "Creating user '$MARKETPLACE_USER'..."
        exec_psql "postgres" "CREATE USER $MARKETPLACE_USER WITH PASSWORD '$MARKETPLACE_PASS';" > /dev/null 2>&1
        success "User '$MARKETPLACE_USER' created"
    fi
}

create_database() {
    if check_database_exists; then
        if [[ "$FORCE_RECREATE" == "true" ]]; then
            warn "Dropping existing database '$MARKETPLACE_DB'..."

            # Terminate existing connections
            exec_psql "postgres" "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$MARKETPLACE_DB' AND pid <> pg_backend_pid();" > /dev/null 2>&1 || true

            exec_psql "postgres" "DROP DATABASE $MARKETPLACE_DB;" > /dev/null 2>&1
            success "Database '$MARKETPLACE_DB' dropped"
        else
            info "Database '$MARKETPLACE_DB' already exists"
            return 0
        fi
    fi

    info "Creating database '$MARKETPLACE_DB'..."
    exec_psql "postgres" "CREATE DATABASE $MARKETPLACE_DB WITH OWNER = $MARKETPLACE_USER ENCODING = 'UTF8' LC_COLLATE = 'en_US.UTF-8' LC_CTYPE = 'en_US.UTF-8' TEMPLATE = template0;" > /dev/null 2>&1 || \
    exec_psql "postgres" "CREATE DATABASE $MARKETPLACE_DB WITH OWNER = $MARKETPLACE_USER ENCODING = 'UTF8';" > /dev/null 2>&1
    success "Database '$MARKETPLACE_DB' created"
}

grant_privileges() {
    info "Granting privileges to '$MARKETPLACE_USER' on '$MARKETPLACE_DB'..."

    exec_psql "postgres" "GRANT ALL PRIVILEGES ON DATABASE $MARKETPLACE_DB TO $MARKETPLACE_USER;" > /dev/null 2>&1
    exec_psql "$MARKETPLACE_DB" "GRANT ALL ON SCHEMA public TO $MARKETPLACE_USER;" > /dev/null 2>&1
    exec_psql "$MARKETPLACE_DB" "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $MARKETPLACE_USER;" > /dev/null 2>&1
    exec_psql "$MARKETPLACE_DB" "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $MARKETPLACE_USER;" > /dev/null 2>&1

    success "Privileges granted"
}

enable_extensions() {
    info "Enabling required PostgreSQL extensions..."

    # Enable UUID extension for generating UUIDs
    exec_psql "$MARKETPLACE_DB" "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";" > /dev/null 2>&1 && \
        success "Extension 'uuid-ossp' enabled" || \
        warn "Could not enable 'uuid-ossp' extension (may not be available)"

    # Enable pg_trgm for fuzzy text search (optional but useful)
    exec_psql "$MARKETPLACE_DB" "CREATE EXTENSION IF NOT EXISTS pg_trgm;" > /dev/null 2>&1 && \
        success "Extension 'pg_trgm' enabled" || \
        warn "Could not enable 'pg_trgm' extension (may not be available)"
}

verify_connection() {
    info "Verifying application user can connect..."

    if PGPASSWORD="$MARKETPLACE_PASS" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$MARKETPLACE_USER" -d "$MARKETPLACE_DB" -c "SELECT current_database(), current_user;" > /dev/null 2>&1; then
        success "Application user can connect to database"
        return 0
    else
        error "Application user cannot connect to database"
        return 1
    fi
}

# =============================================================================
# Main Functions
# =============================================================================

do_check() {
    print_header

    echo "Checking database configuration..."
    echo ""
    echo "  Host:     $POSTGRES_HOST"
    echo "  Port:     $POSTGRES_PORT"
    echo "  Database: $MARKETPLACE_DB"
    echo "  User:     $MARKETPLACE_USER"
    echo ""

    if check_postgres_connection; then
        echo ""
        if check_database_exists; then
            success "Database '$MARKETPLACE_DB' exists"
            if verify_connection; then
                echo ""
                success "All checks passed!"
                return 0
            fi
        else
            warn "Database '$MARKETPLACE_DB' does not exist"
            echo "  Run './init_db.sh' to create it"
            return 1
        fi
    fi
    return 1
}

do_init() {
    print_header

    echo "Configuration:"
    echo "  Host:           $POSTGRES_HOST"
    echo "  Port:           $POSTGRES_PORT"
    echo "  Admin User:     $POSTGRES_USER"
    echo "  Target Database: $MARKETPLACE_DB"
    echo "  App User:       $MARKETPLACE_USER"
    echo ""

    # Check connection first
    if ! check_postgres_connection; then
        exit 1
    fi

    echo ""
    echo "Initializing database..."
    echo ""

    # Create user and database
    if [[ "$SKIP_USER" != "true" ]]; then
        create_user
    fi

    create_database
    grant_privileges
    enable_extensions

    echo ""

    # Verify
    if verify_connection; then
        echo ""
        echo -e "${GREEN}=================================================================${NC}"
        echo -e "${GREEN}  Database initialization complete!${NC}"
        echo -e "${GREEN}=================================================================${NC}"
        echo ""
        echo "Next steps:"
        echo "  1. Run Alembic migrations:"
        echo "     cd src/core/services/policy_marketplace"
        echo "     alembic upgrade head"
        echo ""
        echo "  2. Seed verified templates:"
        echo "     python scripts/seed_templates.py"
        echo ""
        echo "Connection string for .env:"
        echo "  MARKETPLACE_DATABASE_URL=postgresql+asyncpg://$MARKETPLACE_USER:$MARKETPLACE_PASS@$POSTGRES_HOST:$POSTGRES_PORT/$MARKETPLACE_DB"
        echo ""
    else
        error "Database initialization completed but verification failed"
        exit 1
    fi
}

# =============================================================================
# Main Execution
# =============================================================================

FORCE_RECREATE=false
SKIP_USER=false
VERBOSE=false
ACTION="init"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            show_help
            exit 0
            ;;
        --check)
            ACTION="check"
            shift
            ;;
        --force)
            FORCE_RECREATE=true
            shift
            ;;
        --skip-user)
            SKIP_USER=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            set -x
            shift
            ;;
        *)
            error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Execute
case $ACTION in
    check)
        do_check
        ;;
    init)
        do_init
        ;;
esac
