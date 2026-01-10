import os
import sys

import numpy as np
import torch

# Ensure we can import the project modules
sys.path.append("/home/dislove/document/acgs2")

try:
    from acgs2_perf import sinkhorn_knopp

    print("SUCCESS: acgs2_perf imported.")
except ImportError:
    print("FAILURE: acgs2_perf module not found. Building might be required.")
    sys.exit(1)


def test_rust_weighted_sinkhorn():
    print("\nTesting Rust Weighted Sinkhorn...")

    # 2x2 matrix
    W = [[1.0, 1.0], [1.0, 1.0]]  # Uniform input

    # Target marginals (not uniform)
    # Row sums: [0.6, 1.4]
    # Col sums: [0.6, 1.4]
    r = [0.6, 1.4]
    c = [0.6, 1.4]

    try:
        W_out = sinkhorn_knopp(W, row_marginal=r, col_marginal=c, iters=50, eps=1e-8)
        W_tensor = torch.tensor(W_out)

        print("Output Matrix:")
        print(W_tensor)

        # Check row sums
        row_sums = W_tensor.sum(dim=1)
        print(f"Row Sums: {row_sums}")
        assert torch.allclose(row_sums, torch.tensor(r), atol=1e-4), (
            f"Row sums mismatch: {row_sums} vs {r}"
        )

        # Check col sums
        col_sums = W_tensor.sum(dim=0)
        print(f"Col Sums: {col_sums}")
        assert torch.allclose(col_sums, torch.tensor(c), atol=1e-4), (
            f"Col sums mismatch: {col_sums} vs {c}"
        )

        print("SUCCESS: Weighted Sinkhorn converged to target marginals.")
        return True
    except TypeError as e:
        print(f"FAILURE: Signature mismatch? {e}")
        return False
    except Exception as e:
        print(f"FAILURE: Runtime error: {e}")
        return False


if __name__ == "__main__":
    if test_rust_weighted_sinkhorn():
        sys.exit(0)
    else:
        sys.exit(1)
