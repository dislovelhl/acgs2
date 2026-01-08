.PHONY: setup reset-chain verify-policy test lint help

help:
	@echo "Usage:"
	@echo "  make setup        - Install dependencies, configure pre-commit, and seed test environment"
	@echo "  make reset-chain  - Deterministically reset the local blockchain state (simulated)"
	@echo "  make verify-policy - Enforce policy-aware CI gates (checks changelog updates)"
	@echo "  make test         - Run all tests"
	@echo "  make lint         - Run ruff, black, and mypy checks"

setup:
	@echo "Starting project setup..."
	pip install -r src/core/config/requirements_optimized.txt || pip install -e "src/core[dev,test]"
	pre-commit install
	@echo "Seeding test wallets..."
	# Placeholder for wallet seeding logic
	@echo "Setup complete."

reset-chain:
	@echo "Resetting local blockchain state..."
	# Placeholder for cleanup of local node data
	rm -rf .local_chain_data
	mkdir -p .local_chain_data
	@echo "Blockchain reset complete."

verify-policy:
	chmod +x scripts/verify_policy_gates.py
	python3 scripts/verify_policy_gates.py

test:
	pytest tests/

lint:
	ruff check .
	black --check .
	mypy .
