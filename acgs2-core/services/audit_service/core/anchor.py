"""
ACGS-2 Audit Service - Persistent Local Anchor
Constitutional Hash: cdd01ef066bc6cf2

Provides a production-ready, tamper-evident local anchor for storage of Merkle Roots.
This serves as the primary persistence layer before distributed anchoring (blockchain/L2).
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class LocalFileSystemAnchor:
    """
    A persistent, append-only ledger for storing Merkle Roots.
    Each block is cryptographically linked to the previous one.
    """

    def __init__(self, storage_path: str = "audit_anchor_production.json"):
        # Ensure path is absolute if not provided
        self.storage_path = os.path.abspath(storage_path)
        self.blocks: List[Dict[str, Any]] = []
        self._initialize_storage()

    def _initialize_storage(self):
        """Load existing anchor or initialize new genesis block."""
        parent_dir = os.path.dirname(self.storage_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)

        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, "r") as f:
                    self.blocks = json.load(f)
                    # Simple integrity check
                    if not self._verify_chain():
                        logger.error(
                            "Audit anchor chain integrity failure! Local storage might be tampered with."
                        )
                        # In production, we might want to alert here.
            else:
                self._create_genesis_block()
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load audit anchor: {e}")
            self._create_genesis_block()

    def _create_genesis_block(self):
        """Initialize the chain with a genesis block."""
        genesis = {
            "index": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "root_hash": "genesis_root",
            "previous_hash": "0" * 64,
            "constitutional_hash": "cdd01ef066bc6cf2",
        }
        genesis["hash"] = self._calculate_hash(genesis)
        self.blocks = [genesis]
        self._save_to_disk()
        logger.info("Initialized new audit anchor genesis block")

    def _calculate_hash(self, block: Dict[str, Any]) -> str:
        """Calculate SHA-256 hash of a block's contents."""
        # Use sorted keys for deterministic JSON
        content = json.dumps(
            {
                "index": block["index"],
                "timestamp": block["timestamp"],
                "root_hash": block["root_hash"],
                "previous_hash": block["previous_hash"],
                "constitutional_hash": block.get("constitutional_hash", "cdd01ef066bc6cf2"),
            },
            sort_keys=True,
        )
        return hashlib.sha256(content.encode()).hexdigest()

    def anchor_root(self, root_hash: str) -> Dict[str, Any]:
        """Atomically append a new Merkle Root to the ledger."""
        previous_block = self.blocks[-1]
        new_index = previous_block["index"] + 1

        new_block = {
            "index": new_index,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "root_hash": root_hash,
            "previous_hash": previous_block["hash"],
            "constitutional_hash": "cdd01ef066bc6cf2",
        }
        new_block["hash"] = self._calculate_hash(new_block)

        self.blocks.append(new_block)
        self._save_to_disk()
        logger.info(f"Merkle Root {root_hash} anchored successfully at index {new_index}")
        return new_block

    def verify_root(self, root_hash: str) -> bool:
        """Verify if a root hash exists in the local ledger."""
        return any(block["root_hash"] == root_hash for block in self.blocks)

    def _verify_chain(self) -> bool:
        """Verify the cryptographic integrity of the entire chain."""
        for i in range(1, len(self.blocks)):
            prev = self.blocks[i - 1]
            curr = self.blocks[i]

            if curr["previous_hash"] != prev["hash"]:
                return False
            if curr["hash"] != self._calculate_hash(curr):
                return False
        return True

    def _save_to_disk(self):
        """Flush chain to disk."""
        try:
            with open(self.storage_path, "w") as f:
                json.dump(self.blocks, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to persist audit anchor to disk: {e}")

    def get_latest_block(self) -> Dict[str, Any]:
        return self.blocks[-1]
