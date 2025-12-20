"""
ACGS-2 Audit Ledger Service
不可变审计账本实现

核心功能：
- ValidationResult哈希上链
- Merkle Tree批量验证
- 区块链集成准备

Constitutional Hash: cdd01ef066bc6cf2
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple

from .merkle_tree.merkle_tree import MerkleTree

# Import ValidationResult from the canonical source (enhanced_agent_bus)
# This eliminates model duplication across services
try:
    from enhanced_agent_bus.validators import ValidationResult
except ImportError:
    # Fallback for standalone service usage
    from dataclasses import dataclass, field
    from typing import Any, Dict, List

    try:
        from shared.constants import CONSTITUTIONAL_HASH
    except ImportError:
        CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

    @dataclass
    class ValidationResult:
        """Fallback ValidationResult for standalone usage."""
        is_valid: bool = True
        errors: List[str] = field(default_factory=list)
        warnings: List[str] = field(default_factory=list)
        metadata: Dict[str, Any] = field(default_factory=dict)
        constitutional_hash: str = CONSTITUTIONAL_HASH

        def to_dict(self) -> Dict[str, Any]:
            return {
                "is_valid": self.is_valid,
                "errors": self.errors,
                "warnings": self.warnings,
                "metadata": self.metadata,
                "constitutional_hash": self.constitutional_hash,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }


@dataclass
class AuditEntry:
    """Represents a single entry in the audit ledger.

    Attributes:
        validation_result (ValidationResult): The result of the validation.
        hash (str): The SHA-256 hash of the validation result.
        timestamp (float): The Unix timestamp when the entry was created.
        batch_id (Optional[str]): The ID of the batch this entry belongs to.
        merkle_proof (Optional[List[Tuple[str, bool]]]): The Merkle proof for
            this entry within its batch.
    """
    validation_result: ValidationResult
    hash: str
    timestamp: float
    batch_id: Optional[str] = None
    merkle_proof: Optional[List[Tuple[str, bool]]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Converts the audit entry to a dictionary.

        Returns:
            Dict[str, Any]: A dictionary representation of the audit entry.
        """
        return {
            "validation_result": self.validation_result.to_dict(),
            "hash": self.hash,
            "timestamp": self.timestamp,
            "batch_id": self.batch_id,
            "merkle_proof": self.merkle_proof
        }


class AuditLedger:
    """An immutable audit ledger for recording validation results.

    This class manages the storage of validation results, batching them into
    Merkle Trees for efficient verification and blockchain integration.

    Attributes:
        entries (List[AuditEntry]): All audit entries in the ledger.
        batch_size (int): The number of entries per batch.
    """

    def __init__(self, batch_size: int = 100):
        """Initializes the AuditLedger.

        Args:
            batch_size (int): The number of entries to include in each batch.
                Defaults to 100.
        """
        self.entries: List[AuditEntry] = []
        self.current_batch: List[ValidationResult] = []
        self.batch_size = batch_size
        self.merkle_tree: Optional[MerkleTree] = None
        self.batch_counter = 0

    def add_validation_result(self, validation_result: ValidationResult) -> str:
        """
        添加验证结果到审计账本
        返回：条目哈希
        """
        # 创建审计条目
        entry_hash = self._hash_validation_result(validation_result)
        timestamp = time.time()

        entry = AuditEntry(
            validation_result=validation_result,
            hash=entry_hash,
            timestamp=timestamp
        )

        self.entries.append(entry)
        self.current_batch.append(validation_result)

        # 检查是否需要提交批次
        if len(self.current_batch) >= self.batch_size:
            self._commit_batch()

        return entry_hash

    def _hash_validation_result(self, validation_result: ValidationResult) -> str:
        """计算验证结果的哈希"""
        # 创建确定性数据用于哈希（不包含时间戳）
        hash_data = {
            'is_valid': validation_result.is_valid,
            'errors': validation_result.errors,
            'warnings': validation_result.warnings,
            'metadata': validation_result.metadata,
            'constitutional_hash': validation_result.constitutional_hash
        }
        # 序列化为JSON字符串（确保确定性排序）
        data = json.dumps(hash_data, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()

    def _commit_batch(self) -> str:
        """提交当前批次到Merkle Tree"""
        if not self.current_batch:
            return ""

        # 生成批次ID
        batch_id = f"batch_{self.batch_counter}_{int(time.time())}"
        self.batch_counter += 1

        # 创建Merkle Tree（使用与哈希计算相同的数据格式）
        batch_data = []
        for vr in self.current_batch:
            hash_data = {
                'is_valid': vr.is_valid,
                'errors': vr.errors,
                'warnings': vr.warnings,
                'metadata': vr.metadata,
                'constitutional_hash': vr.constitutional_hash
            }
            batch_data.append(json.dumps(hash_data, sort_keys=True).encode())
        self.merkle_tree = MerkleTree(batch_data)

        # 更新条目中的批次信息和Merkle证明
        root_hash = self.merkle_tree.get_root_hash()
        for i, entry in enumerate(self.entries[-len(self.current_batch):]):
            entry.batch_id = batch_id
            if self.merkle_tree:
                entry.merkle_proof = self.merkle_tree.get_proof(i)

        # 清空当前批次
        self.current_batch = []

        # Return batch_id (not root_hash) so callers can use get_entries_by_batch()
        return batch_id

    def get_batch_root_hash(self, batch_id: str) -> Optional[str]:
        """获取批次的根哈希"""
        # 简化实现：返回最新批次的根哈希
        if self.merkle_tree:
            return self.merkle_tree.get_root_hash()
        return None

    def verify_entry(self, entry_hash: str, merkle_proof: List[Tuple[str, bool]],
                    root_hash: str) -> bool:
        """
        验证审计条目
        """
        # 找到对应的条目
        entry = None
        for e in self.entries:
            if e.hash == entry_hash:
                entry = e
                break

        if not entry:
            return False

        # 使用Merkle证明验证 - 使用与_hash_validation_result相同的数据格式
        hash_data = {
            'is_valid': entry.validation_result.is_valid,
            'errors': entry.validation_result.errors,
            'warnings': entry.validation_result.warnings,
            'metadata': entry.validation_result.metadata,
            'constitutional_hash': entry.validation_result.constitutional_hash
        }
        entry_data = json.dumps(hash_data, sort_keys=True).encode()
        return self.merkle_tree.verify_proof(entry_data, merkle_proof, root_hash) \
               if self.merkle_tree else False

    def get_entries_by_batch(self, batch_id: str) -> List[AuditEntry]:
        """获取指定批次的所有条目"""
        return [entry for entry in self.entries if entry.batch_id == batch_id]

    def get_ledger_stats(self) -> Dict[str, Any]:
        """获取账本统计信息"""
        return {
            "total_entries": len(self.entries),
            "current_batch_size": len(self.current_batch),
            "batch_size_limit": self.batch_size,
            "batches_committed": self.batch_counter,
            "current_root_hash": self.merkle_tree.get_root_hash() if self.merkle_tree else None
        }

    def force_commit_batch(self) -> str:
        """强制提交当前批次（即使未达到batch_size）"""
        return self._commit_batch()

    def prepare_blockchain_transaction(self, batch_id: str) -> Dict[str, Any]:
        """
        准备区块链交易数据
        返回包含根哈希和批次信息的交易数据
        """
        root_hash = self.get_batch_root_hash(batch_id)
        entries = self.get_entries_by_batch(batch_id)

        return {
            "batch_id": batch_id,
            "root_hash": root_hash,
            "entry_count": len(entries),
            "timestamp": int(time.time()),
            "entries_hashes": [entry.hash for entry in entries]
        }