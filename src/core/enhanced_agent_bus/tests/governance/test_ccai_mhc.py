import asyncio
import os
import statistics
import sys
from datetime import datetime, timezone

# Add project root to sys.path
sys.path.append("/home/dislove/document/acgs2")

from enhanced_agent_bus.governance.ccai_framework import (
    DeliberationResult,
    DemocraticConstitutionalGovernance,
    StakeholderGroup,
)


async def test_ccai_mhc_integration():
    print("Testing CCAI Framework with mHC Stability...")

    # Initialize governance with mHC
    governance = DemocraticConstitutionalGovernance(consensus_threshold=0.6)

    # 1. Test Dynamic Dimension Resizing
    print("\nScenario 1: Dynamic Resizing (10 stakeholders)")
    stakeholders = []
    for i in range(10):
        s = await governance.register_stakeholder(
            f"Stakeholder_{i}", StakeholderGroup.TECHNICAL_EXPERTS, ["General"]
        )
        stakeholders.append(s)

    proposal = await governance.propose_constitutional_change(
        title="Stability Test 1",
        description="Testing resizing with 10 stakeholders",
        proposed_changes={"param": 1},
        proposer=stakeholders[0],
    )

    result = await governance.run_deliberation(proposal, stakeholders)
    n_clusters = result.clusters_identified

    print(f"Clusters identified: {n_clusters}")
    print(f"Resizing check: stability_layer.dim = {governance.stability_layer.dim}")

    assert governance.stability_layer.dim == n_clusters
    print("Scenario 1 SUCCESS: Stability layer correctly resized.")

    # Check Observability Metrics
    print("\nVerifying Phase 3 Observability Metrics...")
    print(f"Stability Analysis: {result.stability_analysis}")
    assert "stability_hash" in result.stability_analysis, "Missing stability_hash"
    assert "spectral_radius_bound" in result.stability_analysis, "Missing spectral_radius_bound"
    assert result.stability_analysis["spectral_radius_bound"] <= 1.0, "Spectral radius violation"
    print("Observability Check SUCCESS: Stability metrics present and valid.")

    # 2. Test Trust-Weighted Influence
    print("\nScenario 2: Trust-Weighted Influence")
    # Register 2 stakeholders with very different trust
    h_s = await governance.register_stakeholder(
        "HighTrust", StakeholderGroup.TECHNICAL_EXPERTS, ["AI"]
    )
    l_s = await governance.register_stakeholder("LowTrust", StakeholderGroup.END_USERS, ["Usage"])

    # Access and modify trust scores
    h_s.trust_score = 0.9
    l_s.trust_score = 0.1

    proposal2 = await governance.propose_constitutional_change(
        title="Stability Test 2",
        description="Testing trust weighting",
        proposed_changes={"param": 2},
        proposer=h_s,
    )

    print("Running deliberation with trust-weighted stakeholders...")
    result2 = await governance.run_deliberation(proposal2, [h_s, l_s])

    print(f"Clusters: {result2.clusters_identified}")
    print(f"Resizing check: stability_layer.dim = {governance.stability_layer.dim}")

    assert governance.stability_layer.dim == result2.clusters_identified
    print("Scenario 2 SUCCESS: Trust-weighted deliberation executed successfully.")

    print("\nALL CCAI Integration Scenarios PASSED!")
    return True


if __name__ == "__main__":
    try:
        if asyncio.run(test_ccai_mhc_integration()):
            print("\nIntegration test logic completed.")
        else:
            print("\nIntegration test logic FAILED.")
            sys.exit(1)
    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"\nExecution error: {e}")
        sys.exit(1)
