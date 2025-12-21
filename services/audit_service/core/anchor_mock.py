"""
ACGS-2 Audit Service - Blockchain Anchor Mock
Constitutional Hash: cdd01ef066bc6cf2
Simulates a Layer 1 blockchain for permanent root anchoring.
"""

import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import hashlib

logger = logging.getLogger(__name__)

class BlockchainAnchor:
    """
    A persistent, append-only mock of a blockchain for storing Merkle Roots.
    """
    def __init__(self, storage_path: str = "blockchain_anchor.json"):
        self.storage_path = storage_path
        self.blocks: List[Dict[str, Any]] = []
        self._load_anchor()

    def _load_anchor(self):
        try:
            with open(self.storage_path, 'r') as f:
                self.blocks = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Genesis Block
            genesis = {
                "index": 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "root_hash": "genesis_root",
                "previous_hash": "0" * 64,
                "hash": self._calculate_hash(0, "genesis_root", "0" * 64)
            }
            self.blocks = [genesis]
            self._save_anchor()

    def _calculate_hash(self, index: int, root_hash: str, previous_hash: str) -> str:
        content = f"{index}{root_hash}{previous_hash}"
        return hashlib.sha256(content.encode()).hexdigest()

    def anchor_root(self, root_hash: str) -> Dict[str, Any]:
        """Commit a new Merkle Root to the 'blockchain'."""
        previous_block = self.blocks[-1]
        new_index = previous_block["index"] + 1
        
        new_block = {
            "index": new_index,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "root_hash": root_hash,
            "previous_hash": previous_block["hash"],
        }
        new_block["hash"] = self._calculate_hash(new_index, root_hash, previous_block["hash"])
        
        self.blocks.append(new_block)
        self._save_anchor()
        logger.info(f"Root {root_hash} anchored in block {new_index}")
        return new_block

    def verify_root(self, root_hash: str) -> bool:
        """Check if a root hash exists in the anchored blocks."""
        for block in self.blocks:
            if block["root_hash"] == root_hash:
                return True
        return False

    def get_latest_block(self) -> Dict[str, Any]:
        return self.blocks[-1]

    def _save_anchor(self):
        with open(self.storage_path, 'w') as f:
            json.dump(self.blocks, f, indent=2)
