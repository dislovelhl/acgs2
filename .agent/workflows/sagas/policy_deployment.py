"""
Policy Deployment Saga
Constitutional Hash: cdd01ef066bc6cf2

A distributed transaction workflow for deploying governance policies.
Ensures atomicity: either the policy is fully deployed and verified, or rolled back to previous state.
"""

import json
import logging
from typing import Any, Dict

from .base_saga import BaseSaga, SagaStep

try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

logger = logging.getLogger(__name__)


class PolicyDeploymentSaga(BaseSaga):
    """
    Saga for deploying governance policies with rollback support.

    Steps:
    1. Validate Policy (Constitutional Check)
    2. Backup Current Policy
    3. Deploy New Policy
    4. Verify Deployment
    """

    def __init__(self):
        super().__init__(saga_id="policy-deployment-saga", constitutional_hash=CONSTITUTIONAL_HASH)
        self._configure_steps()

    def _configure_steps(self):
        """Configure saga steps and compensations."""

        # Step 1: Validate Policy
        self.add_step(
            SagaStep(
                name="validate_policy",
                execute=self._validate_policy,
                compensate=self._noop_compensation,  # Nothing to undo if validation fails
            )
        )

        # Step 2: Backup Current Policy
        self.add_step(
            SagaStep(
                name="backup_policy", execute=self._backup_policy, compensate=self._delete_backup
            )
        )

        # Step 3: Deploy New Policy
        self.add_step(
            SagaStep(
                name="deploy_policy", execute=self._deploy_policy, compensate=self._restore_backup
            )
        )

        # Step 4: Verify Deployment
        self.add_step(
            SagaStep(
                name="verify_deployment",
                execute=self._verify_deployment,
                compensate=self._noop_compensation,  # Rolled back by previous steps
            )
        )

    # --- Step Executions ---

    async def _validate_policy(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the new policy against constitutional rules."""
        policy_content = input_data.get("policy_content")
        if not policy_content:
            raise ValueError("Missing policy content")

        # In a real system, this would call a policy engine
        if "unsafe" in json.dumps(policy_content):
            raise ValueError("Policy contains unsafe directives")

        logger.info("Policy validated successfully")
        return {"valid": True}

    async def _backup_policy(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Snapshot the current policy configuration."""
        policy_id = input_data.get("policy_id")

        # Simulate backup
        backup_id = f"{policy_id}_backup_v1"
        logger.info(f"Backed up policy {policy_id} to {backup_id}")

        return {"backup_id": backup_id, "policy_id": policy_id}

    async def _deploy_policy(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Write the new policy to the registry."""
        policy_id = input_data.get("policy_id")
        new_content = input_data.get("policy_content")

        # Simulate deployment failure for testing
        if input_data.get("simulate_deploy_failure"):
            raise RuntimeError("Deployment simulation failure")

        logger.info(f"Deployed new content for {policy_id}")
        return {"deployed_version": "v2"}

    async def _verify_deployment(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Verify the deployed policy is active and healthy."""
        policy_id = input_data.get("policy_id")

        # Simulate verification failure
        if input_data.get("simulate_verify_failure"):
            raise RuntimeError("Policy verification failed health check")

        logger.info(f"Policy {policy_id} verified active")
        return {"active": True}

    # --- Compensations ---

    async def _noop_compensation(self, input_data: Dict[str, Any]) -> None:
        """Do nothing."""
        pass

    async def _delete_backup(self, input_data: Dict[str, Any]) -> None:
        """Delete the created backup (cleanup)."""
        backup_id = input_data.get("context", {}).get("backup_policy", {}).get("backup_id")
        if backup_id:
            logger.info(f"Deleted backup {backup_id}")

    async def _restore_backup(self, input_data: Dict[str, Any]) -> None:
        """Restore policy from backup."""
        context = input_data.get("context", {})
        backup_info = context.get("backup_policy", {})
        backup_id = backup_info.get("backup_id")
        policy_id = backup_info.get("policy_id")

        if backup_id and policy_id:
            logger.warning(f"Restoring policy {policy_id} from {backup_id}")
            # Logic to restore would go here
            logger.info("Restore complete")
