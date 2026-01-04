# AI Governance Experiment Scaffold

This directory contains a rigorous, reproducible, and auditable framework for AI governance experiments. It is designed to evaluate constitutional AI governance systems like ACGS.

## Directory Structure

- `data/tasks/`: Standardized task sets (Compliance, Boundary, Non-compliant).
- `src/evaluators/`: Metrics calculation logic.
- `src/crypto/`: Ledger integration and log signing utilities.
- `policies/rego/`: Policy templates for OPA.
- `notebooks/`: Visualization and statistical analysis.
- `reports/`: Generated experiment reports.

## Core Metrics

1. **Blocked Rate**: (Blocked Non-Compliant Actions / Total Non-Compliant Attempts)
2. **Audit Latency**: (Triggered to Logged, p50/p95/p99)
3. **False Positive Rate**: (Compliant Actions Blocked / Total Compliant Attempts)

## Quick Start

1. Define your task set in `data/tasks/`.
2. Configure your policy in `policies/rego/`.
3. Run the evaluation script (to be implemented).
4. Analyze results in the Jupyter Notebook.
