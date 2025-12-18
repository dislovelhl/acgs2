# ACGS-2 Governance Lifecycle & CI/CD Pipeline

**Constitutional Hash**: `cdd01ef066bc6cf2`

## 1. Policy-as-Code CI/CD Pipeline

The following pipeline ensures that all constitutional policies are tested and verified before deployment.

### Stage 1: Validation (Linting)
- **Tool**: `opa check`
- **Action**: Verify Rego syntax and best practices.
- **Failure**: Blocks the pipeline.

### Stage 2: Unit Testing
- **Tool**: `opa test`
- **Action**: Execute all `*_test.rego` files in the `policies/rego` directory.
- **Requirement**: 100% pass rate.

### Stage 3: Compilation & Signing
- **Tool**: `tools/policy_bundle_manager.py`
- **Action**: 
    1. Compile policies into a `.tar.gz` bundle.
    2. Sign the bundle hash using Ed25519 private key (stored in Vault).
    3. Generate metadata including the Constitutional Hash.

### Stage 4: Shadow Mode Execution
- **Action**: Deploy the new bundle to a "Shadow OPA" instance.
- **Logic**: The Agent Bus sends traffic to both Production OPA and Shadow OPA.
- **Monitoring**: Log differences in decisions. If discrepancy > 1%, trigger manual review.

### Stage 5: OCI Distribution
- **Tool**: `oras` / OCI Registry
- **Action**: Push the signed bundle as an OCI artifact.

---

## 2. HITL (Human-In-The-Loop) Workflow

For high-risk actions (Impact Score >= 0.8), the following workflow is enforced:

1.  **Detection**: `DeliberationLayer` identifies high-risk message.
2.  **Pause**: Message is held in `DeliberationQueue`.
3.  **Notification**: `HITLManager` sends an interactive alert to Slack/Teams.
4.  **Review**: Stakeholder reviews the context and reasoning.
5.  **Decision**:
    - **Approve**: Message is released to the Agent Bus.
    - **Reject**: Message is dropped, and the sender is notified.
6.  **Audit**: The decision, reviewer ID, and reasoning are hashed and recorded in the `AuditLedger` (Merkle Tree + Blockchain).

---

## 3. Rollback Mechanism (LKG)

If a newly deployed policy bundle causes system-wide failures or fails signature verification:
1.  `OPAClient` detects the failure.
2.  `_rollback_to_lkg()` is triggered.
3.  The system reloads the `lkg_bundle.tar.gz` from local persistent storage.
4.  An alert is sent to the SRE team.
