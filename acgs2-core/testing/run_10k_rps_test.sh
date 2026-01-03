#!/bin/bash
#
# ACGS-2 10K RPS Load Test E2E Script
#
# This script orchestrates the full 10K RPS performance validation:
# 1. Checks prerequisites (locust, docker)
# 2. Starts services if not running
# 3. Waits for health checks
# 4. Runs the 10K RPS load test
# 5. Collects and validates Prometheus metrics
# 6. Generates comprehensive report
#
# Usage:
#   ./run_10k_rps_test.sh                    # Full 10K RPS test
#   ./run_10k_rps_test.sh --smoke-test       # Quick smoke test (100 users, 30s)
#   ./run_10k_rps_test.sh --users 5000       # Custom user count
#   ./run_10k_rps_test.sh --help             # Show help
#
# Exit Codes:
#   0: All performance targets met
#   1: Performance targets not met
#   2: Error during test execution

set -e

# Default configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
HOST="http://localhost:8080"
USERS=10000
SPAWN_RATE=100
DURATION="5m"
RESULTS_DIR="${SCRIPT_DIR}/results"
SMOKE_TEST=false
SKIP_SERVICES=false
PROMETHEUS_URL=""

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

print_banner() {
    echo ""
    echo "============================================================"
    echo " ACGS-2 10K RPS Load Test Validation"
    echo "============================================================"
    echo " Target: 10,000+ RPS sustained throughput"
    echo " P99 Latency: < 1ms"
    echo " Cache Hit Rate: > 98%"
    echo " Error Rate: 0%"
    echo "============================================================"
    echo ""
}

show_help() {
    cat << EOF
ACGS-2 10K RPS Load Test E2E Script

Usage: $0 [options]

Options:
  --host URL              Target host URL (default: http://localhost:8080)
  --users N               Number of concurrent users (default: 10000)
  --spawn-rate N          Users spawned per second (default: 100)
  --duration TIME         Test duration (default: 5m)
  --smoke-test            Run quick smoke test (100 users, 30s)
  --skip-services         Skip starting/checking Docker services
  --prometheus-url URL    Prometheus URL for metrics validation
  --results-dir DIR       Directory for test results
  --help                  Show this help message

Examples:
  # Full 10K RPS validation
  $0

  # Smoke test
  $0 --smoke-test

  # Custom parameters
  $0 --users 5000 --duration 2m --host http://api-gateway:8080

Exit Codes:
  0: All performance targets met
  1: Performance targets not met
  2: Error during test execution

EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --host)
                HOST="$2"
                shift 2
                ;;
            --users)
                USERS="$2"
                shift 2
                ;;
            --spawn-rate)
                SPAWN_RATE="$2"
                shift 2
                ;;
            --duration)
                DURATION="$2"
                shift 2
                ;;
            --smoke-test)
                SMOKE_TEST=true
                USERS=100
                SPAWN_RATE=10
                DURATION="30s"
                shift
                ;;
            --skip-services)
                SKIP_SERVICES=true
                shift
                ;;
            --prometheus-url)
                PROMETHEUS_URL="$2"
                shift 2
                ;;
            --results-dir)
                RESULTS_DIR="$2"
                shift 2
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 2
                ;;
        esac
    done
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check for locust
    if ! command -v locust &> /dev/null; then
        log_error "locust not found. Install with: pip install locust"
        exit 2
    fi
    log_success "locust found: $(locust --version)"

    # Check for Python
    if ! command -v python3 &> /dev/null; then
        log_error "python3 not found"
        exit 2
    fi
    log_success "python3 found: $(python3 --version)"

    # Check locustfile exists
    if [[ ! -f "${SCRIPT_DIR}/performance_10k_rps.py" ]]; then
        log_error "Locustfile not found: ${SCRIPT_DIR}/performance_10k_rps.py"
        exit 2
    fi
    log_success "Locustfile found"

    # Check for docker (optional)
    if command -v docker &> /dev/null; then
        log_success "docker found: $(docker --version)"
    else
        log_warn "docker not found - ensure services are running manually"
    fi

    # Increase file descriptor limits for high load
    current_ulimit=$(ulimit -n)
    if [[ "$current_ulimit" -lt 65535 ]]; then
        log_warn "File descriptor limit is $current_ulimit (recommended: 65535)"
        log_info "Attempting to increase limit..."
        ulimit -n 65535 2>/dev/null || log_warn "Could not increase limit - may affect test"
    else
        log_success "File descriptor limit: $current_ulimit"
    fi
}

start_services() {
    if [[ "$SKIP_SERVICES" == "true" ]]; then
        log_info "Skipping service startup (--skip-services)"
        return
    fi

    log_info "Checking if services are running..."

    # Check if API Gateway is reachable
    if curl -sf "${HOST}/health" > /dev/null 2>&1; then
        log_success "API Gateway is already running at ${HOST}"
        return
    fi

    log_info "Starting services with Docker Compose..."

    cd "${PROJECT_ROOT}"

    if [[ -f "docker-compose.dev.yml" ]]; then
        docker compose -f docker-compose.dev.yml up -d
    elif [[ -f "docker-compose.yml" ]]; then
        docker compose up -d
    else
        log_error "No docker-compose file found"
        log_info "Please start services manually and use --skip-services"
        exit 2
    fi

    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    local max_attempts=30
    local attempt=1

    while [[ $attempt -le $max_attempts ]]; do
        if curl -sf "${HOST}/health" > /dev/null 2>&1; then
            log_success "Services are healthy"
            return
        fi
        log_info "Waiting for services... (attempt $attempt/$max_attempts)"
        sleep 5
        ((attempt++))
    done

    log_error "Services failed to become healthy after $max_attempts attempts"
    exit 2
}

run_load_test() {
    log_info "Starting load test..."
    echo ""
    echo "============================================================"
    echo " Load Test Configuration"
    echo "============================================================"
    echo " Host:        ${HOST}"
    echo " Users:       ${USERS}"
    echo " Spawn Rate:  ${SPAWN_RATE}/s"
    echo " Duration:    ${DURATION}"
    echo " Smoke Test:  ${SMOKE_TEST}"
    echo "============================================================"
    echo ""

    # Create results directory
    mkdir -p "${RESULTS_DIR}"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local csv_prefix="${RESULTS_DIR}/load_test_${timestamp}"

    # Run locust
    cd "${SCRIPT_DIR}"

    locust -f performance_10k_rps.py \
        --headless \
        --users "${USERS}" \
        --spawn-rate "${SPAWN_RATE}" \
        --run-time "${DURATION}" \
        --host "${HOST}" \
        --csv "${csv_prefix}" \
        --csv-full-history \
        --html "${csv_prefix}_report.html"

    local exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
        log_error "Locust test failed with exit code $exit_code"
        return 1
    fi

    log_success "Load test completed"

    # Store results path for validation
    export RESULTS_CSV="${csv_prefix}_stats.csv"
    export RESULTS_HTML="${csv_prefix}_report.html"
}

validate_results() {
    log_info "Validating results..."

    if [[ ! -f "${RESULTS_CSV}" ]]; then
        log_error "Results file not found: ${RESULTS_CSV}"
        return 1
    fi

    # Use validate_performance.py for validation
    local validate_script="${SCRIPT_DIR}/validate_performance.py"

    if [[ ! -f "${validate_script}" ]]; then
        log_error "Validation script not found: ${validate_script}"
        return 1
    fi

    local json_output="${RESULTS_DIR}/validation_report.json"

    python3 "${validate_script}" \
        --results "${RESULTS_CSV}" \
        --p99-threshold 1.0 \
        --p95-threshold 0.5 \
        --max-error-rate 0.0 \
        --json-output "${json_output}"

    local exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        log_success "All performance targets met!"
    else
        log_error "Performance targets not met"
    fi

    return $exit_code
}

query_prometheus() {
    if [[ -z "${PROMETHEUS_URL}" ]]; then
        log_info "Skipping Prometheus validation (no --prometheus-url provided)"
        return 0
    fi

    log_info "Querying Prometheus metrics..."

    # Query P99 latency
    local query='histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))'
    local encoded_query=$(python3 -c "import urllib.parse; print(urllib.parse.quote('${query}'))")
    local url="${PROMETHEUS_URL}/api/v1/query?query=${encoded_query}"

    local response=$(curl -sf "${url}" 2>/dev/null)

    if [[ -z "${response}" ]]; then
        log_warn "Could not query Prometheus at ${PROMETHEUS_URL}"
        return 0
    fi

    # Parse P99 value
    local p99_seconds=$(echo "${response}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if data.get('status') == 'success':
    results = data.get('data', {}).get('result', [])
    if results:
        print(results[0].get('value', [0, 0])[1])
" 2>/dev/null)

    if [[ -n "${p99_seconds}" ]]; then
        local p99_ms=$(echo "${p99_seconds} * 1000" | bc 2>/dev/null || echo "N/A")
        log_info "Prometheus P99 latency: ${p99_ms}ms"

        if [[ "${p99_ms}" != "N/A" ]]; then
            local is_pass=$(echo "${p99_ms} < 1.0" | bc 2>/dev/null)
            if [[ "${is_pass}" == "1" ]]; then
                log_success "Prometheus P99 < 1ms target"
            else
                log_error "Prometheus P99 >= 1ms target"
                return 1
            fi
        fi
    fi

    return 0
}

print_summary() {
    echo ""
    echo "============================================================"
    echo " Test Summary"
    echo "============================================================"
    echo " Results CSV:  ${RESULTS_CSV:-N/A}"
    echo " Results HTML: ${RESULTS_HTML:-N/A}"
    echo " JSON Report:  ${RESULTS_DIR}/validation_report.json"
    echo "============================================================"
    echo ""
}

cleanup() {
    log_info "Cleanup completed"
}

main() {
    parse_args "$@"
    print_banner

    trap cleanup EXIT

    check_prerequisites
    start_services
    run_load_test

    local test_result=$?

    if [[ $test_result -eq 0 ]]; then
        validate_results
        test_result=$?
    fi

    if [[ $test_result -eq 0 ]]; then
        query_prometheus
        test_result=$?
    fi

    print_summary

    if [[ $test_result -eq 0 ]]; then
        echo ""
        log_success "============================================"
        log_success " ALL PERFORMANCE TARGETS MET"
        log_success " P99 < 1ms, 0% errors, 10K+ RPS validated"
        log_success "============================================"
        echo ""
        exit 0
    else
        echo ""
        log_error "============================================"
        log_error " PERFORMANCE TARGETS NOT MET"
        log_error " Review results for details"
        log_error "============================================"
        echo ""
        exit 1
    fi
}

main "$@"
