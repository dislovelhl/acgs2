# ACGS-2 Tech Stack

## Backend
- **Language**: Python 3.11+ (3.13 ready)
- **Framework**: FastAPI
- **Database**: PostgreSQL with Row-Level Security
- **Cache**: Redis (multi-tier L1/L2/L3)
- **Policy Engine**: OPA (Open Policy Agent) with Rego
- **Optional**: Rust backend for high-performance message processing

## Frontend (Folo Platform)
- **Web**: TypeScript/React with Next.js
- **Mobile**: React Native/Expo
- **Build**: Turbo monorepo with pnpm

## Infrastructure
- **Containerization**: Docker, Docker Compose
- **Orchestration**: Kubernetes
- **CI/CD**: GitHub Actions, GitLab CI
- **Monitoring**: Prometheus + Grafana

## Key Dependencies
- pydantic (data validation)
- asyncio (async operations)
- pytest (testing)
- redis-py (Redis client)
