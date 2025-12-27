# ACGS-2 Operations Guide: Air-gapped and Disconnected Environments

This guide provides technical specifications and workflows for deploying the ACGS-2 platform in secured, air-gapped, or network-disconnected environments.

## 1. Prerequisites for Air-gapped Deployment

### 1.1 Infrastructure Requirements
- **Hardware**: Dedicated high-trust server nodes with TPM 2.0.
- **Internal Network**: 10Gbps low-latency air-gapped subnet.
- **Storage**: Persistent encrypted block storage (for OCI Registry and Audit Ledger).

### 1.2 Binary Assets
Before entering the air-gapped zone, you must stage the following assets:
- **ACGS-2 Images**: All service container images.
- **OPA Binary**: Statically linked Open Policy Agent binary.
- **Base Policy Bundles**: Standard constitutional and industry-specific OCI bundles.
- **CA Certificates**: Root and Intermediate CA certs for SPIFFE/SVID generation.

## 2. OCI Registry Mirroring Workflow

In a disconnected environment, all ACGS-2 services must pull bundles from an internal OCI-compliant registry (e.g., Harbor or Zot).

### 2.1 Mirroring Strategy
1. **Export**: On a connected machine, use `docker save` or `oras pull` to package images/bundles.
2. **Transfer**: Move the compressed tarballs via secure physical media.
3. **Import**: On the internal registry, run:
   ```bash
   oras push local-registry.acgs.internal/governance/constitutional-rego:v1.0.0 ./rego-bundle.tar.gz
   ```

### 2.2 Bundle Trust Pinning
Update service configurations to pin the internal registry:
```yaml
# config.yaml (internal)
registry:
  url: "https://local-registry.acgs.internal"
  trust_pin: "sha256:8fc7..." # Digest of the internal root CA
```

## 3. Manual SVID (JWT) Bootstrapping

Since external SPIFFE controllers may be unavailable, manual bootstrapping of agent identities is required.

### 3.1 Initial Key Generation
Generate the platform master key on a Hardware Security Module (HSM) or secure offline node:
```bash
# Using ACGS-2 Crypto Service Offline
python3 -m acgs2.crypto generate-keypair --out ./platform_master.key
```

### 3.2 Manual Agent Onboarding
For each agent, issue a long-lived bootstrap token:
```bash
# Example for Agent 'guardian-01'
python3 -m acgs2.crypto issue-token \
  --agent-id "guardian-01" \
  --tenant-id "internal-secure" \
  --days 365 \
  --private-key ./platform_master.key
```

## 4. Offline Installation Workflow

1. **Deploy Core Services**: Start the Audit Service, Policy Registry, and Deliberation Layer.
2. **Seed Local Registry**: Push the mirrored bundles to the internal registry.
3. **Configure Bus**: Set `USE_DYNAMIC_POLICY=True` and point to the internal registry URL.
4. **Register Agents**: Use the manually bootstrapped SVIDs for the initial registration.

---
**Constitutional Hash Verification**: Always verify the hash `cdd01ef066bc6cf2` after bootstrap.
