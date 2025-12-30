"""
ACGS-2 Audit Service - Anchor Verification CLI
Constitutional Hash: cdd01ef066bc6cf2
CLI tool to verify a Merkle Root against the anchored blockchain.
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from services.audit_service.core.anchor_mock import BlockchainAnchor


def verify_root(root_hash: str):
    anchor = BlockchainAnchor()
    if anchor.verify_root(root_hash):
        print(f"✅ ROOT VERIFIED: Hash {root_hash} is found in the blockchain anchor.")
        # Find the block
        for block in anchor.blocks:
            if block["root_hash"] == root_hash:
                print(f"   Block Index: {block['index']}")
                print(f"   Timestamp:   {block['timestamp']}")
                print(f"   Block Hash:  {block['hash']}")
                break
    else:
        print(f"❌ VERIFICATION FAILED: Hash {root_hash} NOT found in the blockchain anchor.")


def list_blocks():
    anchor = BlockchainAnchor()
    print(f"Blockchain Anchor: {len(anchor.blocks)} blocks")
    print("-" * 60)
    for block in anchor.blocks:
        print(f"B[{block['index']}] | {block['timestamp']} | Root: {block['root_hash'][:16]}...")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Verify Merkle Roots against ACGS-2 Blockchain Anchor"
    )
    subparsers = parser.add_subparsers(dest="command")

    verify_parser = subparsers.add_parser("verify", help="Verify a root hash")
    verify_parser.add_argument("hash", help="The Merkle Root hash to verify")

    list_parser = subparsers.add_parser("list", help="List all anchored blocks")

    args = parser.parse_args()

    if args.command == "verify":
        verify_root(args.hash)
    elif args.command == "list":
        list_blocks()
    else:
        parser.print_help()
