# Add Authentication to Policy Validation API Endpoints

## Overview

The policy check API endpoints (/api/policy/validate, /api/policy/policies, /api/policy/policies/{policy_id}, /api/policy/health) in integration-service/src/api/policy_check.py are publicly accessible without any authentication. These endpoints allow validation of resources against governance policies and listing of available policies.

## Rationale

Public access to policy validation endpoints exposes the governance policy structure and rules to unauthenticated users. Attackers could probe the system to understand policy bypass techniques, enumerate internal policies, or use the service for reconnaissance before launching targeted attacks.

---
*This spec was created from ideation and is pending detailed specification.*
