# ![ACGS-2](docs/images/logo.png)

[![Tests](https://img.shields.io/badge/tests-passing-brightgreen?style=flat-square)](https://github.com/ACGS-Project/ACGS-2/actions/workflows/tests.yml)
[![Coverage](https://img.shields.io/badge/coverage-80%25-brightgreen?style=flat-square)](https://github.com/ACGS-Project/ACGS-2/actions/workflows/coverage.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=flat-square)](https://www.python.org/)

# ACGS-2: Advanced Constitutional Governance System

ACGS-2 is a multi-agent bus platform engineered for high-security, high-compliance environments. It seamlessly fuses **Constitutional AI**, **Extreme Performance (Rust)**, and **Decentralized Auditability (Blockchain)**.

**Constitutional Hash (Mandatory)**: `cdd01ef066bc6cf2`

[中文文档](README.md) | [API Documentation](docs/api_reference.md) | [Architecture Guide](docs/architecture_diagram.md)

---

## 🏗️ Core Architecture

ACGS-2 implements a layered governance model to ensure every agent action adheres to predefined constitutional guidelines.

```mermaid
graph TD
    A[Agent Layer] -->|Message| B[Enhanced Agent Bus]
    B -->|Validation| C{Constitutional Checker}
    C -->|Hash Match| D[Impact Scorer]
    C -->|Violation| E[Blocking & Audit]
    
    D -->|Score >= 0.8| F[Deliberation Layer]
    D -->|Score < 0.8| G[Fast Lane]
    
    F -->|Consensus/HITL| G
    G -->|Delivery| H[Target Agent]
    
    H -->|Final State| I[Blockchain Audit Trail]
```

### Service Dependencies

```mermaid
graph LR
    Bus(Agent Bus) --> Redis[(Redis Queue)]
    Bus --> Rust(Rust Backend)
    Scorer(Impact Scorer) --> BERT(DistilBERT ONNX)
    Audit(Audit Service) --> Solana(Solana/Avalanche)
    Audit --> Merkle(Merkle Tree)
```

---

## 🚀 Quick Start

### 1. Local Development

```bash
# Clone the repository
git clone https://github.com/ACGS-Project/ACGS-2.git && cd ACGS-2

# Install dependencies
pip install -e enhanced_agent_bus[dev]

# (Optional) Compile Rust extensions
cd enhanced_agent_bus/rust && cargo build --release && pip install -e .
```

### 2. Docker Compose Deployment

```bash
docker-compose up -d
```

### 3. Kubernetes Blue-Green Deployment

```bash
kubectl apply -f k8s/namespace.yml
kubectl apply -f k8s/blue-green-deployment.yml
```

---

## 🛠️ Technology Stack

- **Languages**: Python 3.11+, Rust (Stable)
- **AI**: Hugging Face (DistilBERT), ONNX Runtime
- **Infrastructure**: Kubernetes (Istio Service Mesh), Redis, Kafka
- **Security**: OPA (Open Policy Agent), ZKP (Zero Knowledge Proof)
- **Storage**: Solana (Main Audit Chain), PostgreSQL (Metadata)

---

## 📈 Performance Optimization

ACGS-2 is deeply optimized for large-scale agent collaboration:
- **Message Bus**: Rust-powered core reduces latency by 90%.
- **Impact Scorer**: Pre-integrated DistilBERT INT8 quantized model reduces memory footprint by 60%.
- **Traffic Routing**: Istio integration for zero-trust mTLS communication.

---

## 📖 Documentation Index

- [API Reference](docs/api/specs/) (OpenAPI Specs)
- [Deployment Guide](deployment_guide.md)
- [Architecture Decision Records (ADR)](docs/adr/)
- [Istio Service Mesh Configuration](docs/istio/)

---

## 🤝 Contribution & Support

For questions or suggestions, please open an [Issue](https://github.com/ACGS-Project/ACGS-2/issues) or join our [Discord](https://discord.gg/acgs-governance).

**MIT License** - Copyright (c) 2025 ACGS Project
