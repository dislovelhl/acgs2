# 🚀 Getting Started with ACGS-2

Welcome to the Advanced Constitutional Governance System (ACGS-2). This guide will help you get up and running quickly, whether you're a developer, security researcher, or compliance officer.

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11+** (3.13 recommended)
- **Docker & Docker Compose**
- **Git**
- **LLM API Key** (OpenAI or Anthropic)

## ⚡ Quick Setup (Local Development)

The fastest way to explore ACGS-2 is via the local development setup.

### 1. Clone & Install

```bash
git clone https://github.com/dislovelhl/acgs2.git
cd ACGS-2/src/core
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Configure Environment

Create a `.env` file in the root with your API keys:

```bash
OPENAI_API_KEY=sk-...
# or
ANTHROPIC_API_KEY=sk-ant-...
REDIS_URL=redis://localhost:6379
```

### 3. Run Your First Verification

Try the new verification demo to see ACGS-2 in action:

```bash
python examples/verification_demo.py
```

## 🏗️ Deployment Options

### Docker Compose (All Services)

Start the full stack (Agent Bus, Core Governance, API Gateway, Redis) with one command:

```bash
docker compose -f docker-compose.dev.yml up -d
```

### Kubernetes (Production)

For production-grade deployments with full security hardening:

```bash
helm repo add acgs2 https://charts.acgs2.org
helm install acgs2 acgs2/acgs2 --namespace acgs2-system --create-namespace
```

## 🔍 Key Concepts

- **Constitutional Hash**: The immutable anchor for all governance decisions. Defaults to `cdd01ef066bc6cf2`.
- **PACAR**: The multi-turn deliberation protocol used for high-risk AI decisions.
- **Adaptive Governance**: ML-powered risk assessment that adjusts security levels in real-time.

## 📚 Next Steps

- [Security Hardening Guide](./docs/security/SECURITY_HARDENING.md)
- [Performance Benchmarking Report](./src/core/scripts/README_performance.md)
- [Compliance Templates](./src/core/docs/compliance/templates/)
- [C4 Architecture Documentation](./architecture/c4/)

## 🆘 Support

- GitHub Issues: [Report a bug](https://github.com/dislovelhl/acgs2/issues)
- Enterprise Support: [enterprise@acgs2.org](mailto:enterprise@acgs2.org)
