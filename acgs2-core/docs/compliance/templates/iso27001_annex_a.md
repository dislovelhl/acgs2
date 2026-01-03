# ACGS-2 ISO/IEC 27001:2022 Annex A Control Evidence Template

## Annex A Controls

### A.5 Organizational controls

| Control | Name                                       | Implementation Detail                                | Audit Evidence (ACGS-2)                |
| :------ | :----------------------------------------- | :--------------------------------------------------- | :------------------------------------- |
| A.5.1   | Policies for information security          | Constitutional policies stored in `PolicyRegistry`.  | `acgs2-core/services/policy_registry/` |
| A.5.3   | Segregation of duties                      | Multi-turn verifier roles (Red Team vs Validator).   | `PACARVerifier` stages                 |
| A.5.8   | Information security in project management | Mandatory constitutional hash validation in all PRs. | CI/CD logs with hash check             |

### A.8 Technological controls

| Control | Name                     | Implementation Detail                         | Audit Evidence (ACGS-2)              |
| :------ | :----------------------- | :-------------------------------------------- | :----------------------------------- |
| A.8.2   | Privileged access rights | Token-based escalation with audit logging.    | `AuthService` logs                   |
| A.8.10  | Information deletion     | Tenant-isolated data purge routines.          | `StorageProvider.delete_tenant_data` |
| A.8.15  | Logging                  | Structured JSON logging with correlation IDs. | ELK/Datadog logs                     |
| A.8.16  | Monitoring activities    | Real-time health scoring and alerting.        | Grafana dashboards                   |

## Compliance Checklists

Refer to `docs/compliance/guidelines.md` for full implementation requirements.
