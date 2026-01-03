# ACGS-2 Performance Testing Makefile
#
# Targets for running 10K RPS load tests and performance validation
#
# Usage:
#   make help                  # Show available targets
#   make smoke-test            # Quick smoke test (100 users, 30s)
#   make load-test-10k         # Full 10K RPS test (5 minutes)
#   make validate-performance  # Validate existing results
#   make clean                 # Clean up test results

.PHONY: help smoke-test load-test-10k load-test-5k load-test-20k \
        validate-performance simulate-test check-prerequisites \
        start-services stop-services clean

# Default host for load testing
HOST ?= http://localhost:8080
PROMETHEUS_URL ?=
RESULTS_DIR ?= $(CURDIR)/results

# Performance targets
P99_TARGET_MS ?= 1.0
P95_TARGET_MS ?= 0.5
MAX_ERROR_RATE ?= 0.0

help:
	@echo "ACGS-2 Performance Testing Makefile"
	@echo "===================================="
	@echo ""
	@echo "Available targets:"
	@echo "  smoke-test            Quick smoke test (100 users, 30s)"
	@echo "  load-test-10k         Full 10K RPS test (5 minutes)"
	@echo "  load-test-5k          5K RPS test (3 minutes)"
	@echo "  load-test-20k         20K RPS horizontal scaling test"
	@echo "  validate-performance  Validate existing Locust results"
	@echo "  simulate-test         Simulate test for validation script testing"
	@echo "  check-prerequisites   Check required tools are installed"
	@echo "  start-services        Start Docker services"
	@echo "  stop-services         Stop Docker services"
	@echo "  clean                 Clean up test results"
	@echo ""
	@echo "Configuration (via environment):"
	@echo "  HOST=$(HOST)"
	@echo "  PROMETHEUS_URL=$(PROMETHEUS_URL)"
	@echo "  RESULTS_DIR=$(RESULTS_DIR)"
	@echo "  P99_TARGET_MS=$(P99_TARGET_MS)"
	@echo ""
	@echo "Examples:"
	@echo "  make smoke-test HOST=http://api-gateway:8080"
	@echo "  make load-test-10k PROMETHEUS_URL=http://localhost:9090"

check-prerequisites:
	@echo "Checking prerequisites..."
	@command -v locust >/dev/null 2>&1 || { echo "locust not found. Install: pip install locust"; exit 1; }
	@command -v python3 >/dev/null 2>&1 || { echo "python3 not found"; exit 1; }
	@echo "All prerequisites met!"

start-services:
	@echo "Starting services..."
	@cd ../.. && docker compose -f docker-compose.dev.yml up -d
	@echo "Waiting for services to be healthy..."
	@sleep 10
	@curl -sf $(HOST)/health > /dev/null || { echo "Services not healthy"; exit 1; }
	@echo "Services are running!"

stop-services:
	@echo "Stopping services..."
	@cd ../.. && docker compose -f docker-compose.dev.yml down

smoke-test: check-prerequisites
	@echo "Running smoke test (100 users, 30s)..."
	@mkdir -p $(RESULTS_DIR)
	python3 run_10k_rps_validation.py \
		--host $(HOST) \
		--smoke-test \
		--output $(RESULTS_DIR)/smoke_test_report.json

load-test-5k: check-prerequisites
	@echo "Running 5K RPS load test (3 minutes)..."
	@mkdir -p $(RESULTS_DIR)
	python3 run_10k_rps_validation.py \
		--host $(HOST) \
		--users 5000 \
		--spawn-rate 50 \
		--duration 3m \
		--output $(RESULTS_DIR)/load_test_5k_report.json

load-test-10k: check-prerequisites
	@echo "Running 10K RPS load test (5 minutes)..."
	@echo "Target: P99 < 1ms, 0% errors, 10K+ RPS"
	@mkdir -p $(RESULTS_DIR)
	python3 run_10k_rps_validation.py \
		--host $(HOST) \
		--users 10000 \
		--spawn-rate 100 \
		--duration 5m \
		$(if $(PROMETHEUS_URL),--prometheus-url $(PROMETHEUS_URL),) \
		--output $(RESULTS_DIR)/load_test_10k_report.json

load-test-20k: check-prerequisites
	@echo "Running 20K RPS horizontal scaling test (5 minutes)..."
	@echo "Requires 2x API Gateway instances"
	@mkdir -p $(RESULTS_DIR)
	locust -f performance_20k_rps_horizontal.py \
		--headless \
		--users 20000 \
		--spawn-rate 200 \
		--run-time 5m \
		--host $(HOST) \
		--csv $(RESULTS_DIR)/load_test_20k \
		--csv-full-history

validate-performance:
	@echo "Validating performance results..."
	@if [ -z "$(RESULTS_FILE)" ]; then \
		echo "Usage: make validate-performance RESULTS_FILE=path/to/stats.csv"; \
		exit 1; \
	fi
	python3 validate_performance.py \
		--results $(RESULTS_FILE) \
		--p99-threshold $(P99_TARGET_MS) \
		--p95-threshold $(P95_TARGET_MS) \
		--max-error-rate $(MAX_ERROR_RATE) \
		--json-output $(RESULTS_DIR)/validation_report.json

simulate-test:
	@echo "Running simulated test (for validation script testing)..."
	@mkdir -p $(RESULTS_DIR)
	python3 run_10k_rps_validation.py \
		--simulate \
		--output $(RESULTS_DIR)/simulated_report.json

clean:
	@echo "Cleaning up test results..."
	@rm -rf $(RESULTS_DIR)/*.csv $(RESULTS_DIR)/*.json $(RESULTS_DIR)/*.html
	@echo "Cleaned!"
