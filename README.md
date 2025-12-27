# ACGS-2: Antigravity Constitutional Governance System

Welcome to the modularized ACGS-2 repository. The system has been split into dedicated functional repositories to improve maintainability and scalability.

## Repository Structure

The project is organized into four main components:

| Component                                        | Description                            | Primary Contents                                                 |
| :----------------------------------------------- | :------------------------------------- | :--------------------------------------------------------------- |
| [**acgs2-core**](./acgs2-core)                   | Core application logic and services.   | Agent Bus, Policy Registry, Constitutional Services, Shared Libs |
| [**acgs2-infra**](./acgs2-infra)                 | Infrastructure as Code and Deployment. | Terraform, K8s manifests, Helm charts                            |
| [**acgs2-observability**](./acgs2-observability) | Monitoring and system state.           | Dashboards, Alerts, Monitoring tests                             |
| [**acgs2-research**](./acgs2-research)           | Research papers and technical specs.   | Documentation, Model evaluation data                             |

## Getting Started

### Unified Test Runner

To verify the entire system integrity, use the root test runner:

```bash
python3 test_all.py
```

### Components

- **Core Services**: Navigate to `acgs2-core` for service development.
- **Infrastructure**: See `acgs2-infra` for deployment instructions.
- **Monitoring**: Check `acgs2-observability` for system health metrics.

## Documentation

Each repository contains its own detailed `README.md` and documentation in `docs/`.
