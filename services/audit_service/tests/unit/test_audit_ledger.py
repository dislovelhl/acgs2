import unittest
from services.audit_service.core.audit_ledger import AuditLedger, ValidationResult


class TestAuditLedger(unittest.TestCase):
    """AuditLedger单元测试"""

    def setUp(self):
        """测试前准备"""
        self.ledger = AuditLedger(batch_size=3)  # 小批次大小便于测试

    def test_add_single_validation_result(self):
        """测试添加单个验证结果"""
        vr = ValidationResult(is_valid=True, metadata={"test": "data"})
        entry_hash = self.ledger.add_validation_result(vr)

        self.assertIsNotNone(entry_hash)
        self.assertEqual(len(self.ledger.entries), 1)
        self.assertEqual(len(self.ledger.current_batch), 1)

        entry = self.ledger.entries[0]
        self.assertEqual(entry.validation_result, vr)
        self.assertEqual(entry.hash, entry_hash)

    def test_batch_commitment(self):
        """测试批次提交"""
        # 添加足够条目触发批次提交
        for i in range(3):
            vr = ValidationResult(is_valid=True,
                                metadata={"index": i})
            self.ledger.add_validation_result(vr)

        # 检查批次是否已提交
        self.assertEqual(len(self.ledger.current_batch), 0)
        self.assertIsNotNone(self.ledger.merkle_tree)

        # 检查所有条目都有批次ID
        for entry in self.ledger.entries:
            self.assertIsNotNone(entry.batch_id)
            self.assertIsNotNone(entry.merkle_proof)

    def test_entry_verification(self):
        """测试条目验证"""
        # 添加条目并提交批次
        vr = ValidationResult(is_valid=True, metadata={"test": "verification"})
        entry_hash = self.ledger.add_validation_result(vr)
        batch_id = self.ledger.force_commit_batch()

        # 获取条目和证明
        entry = self.ledger.entries[0]
        proof = entry.merkle_proof

        # 获取实际的merkle root hash用于验证
        root_hash = self.ledger.get_batch_root_hash(batch_id)
        self.assertIsNotNone(root_hash)

        # 验证条目
        # 对于单节点树，证明是空列表
        is_valid = self.ledger.verify_entry(entry_hash, proof, root_hash)
        self.assertTrue(is_valid)

    def test_invalid_verification(self):
        """测试无效验证"""
        # 添加条目
        vr = ValidationResult(is_valid=True, metadata={"test": "invalid"})
        self.ledger.add_validation_result(vr)
        batch_id = self.ledger.force_commit_batch()

        entry = self.ledger.entries[0]
        root_hash = self.ledger.get_batch_root_hash(batch_id)

        # 使用错误的哈希验证
        wrong_hash = "wrong_hash"
        is_valid = self.ledger.verify_entry(wrong_hash, entry.merkle_proof, root_hash)
        self.assertFalse(is_valid)

        # 使用错误的根哈希验证
        wrong_root = "wrong_root_hash"
        is_valid = self.ledger.verify_entry(entry.hash, entry.merkle_proof, wrong_root)
        self.assertFalse(is_valid)

    def test_get_entries_by_batch(self):
        """测试按批次获取条目"""
        # 添加多个批次的条目
        for batch in range(2):
            for i in range(2):
                vr = ValidationResult(is_valid=True,
                                    metadata={"batch": batch, "index": i})
                self.ledger.add_validation_result(vr)
            self.ledger.force_commit_batch()

        # 检查批次
        batch_ids = set(entry.batch_id for entry in self.ledger.entries if entry.batch_id)
        self.assertGreater(len(batch_ids), 0)

        # 获取特定批次的条目
        for batch_id in batch_ids:
            entries = self.ledger.get_entries_by_batch(batch_id)
            self.assertGreater(len(entries), 0)
            for entry in entries:
                self.assertEqual(entry.batch_id, batch_id)

    def test_ledger_stats(self):
        """测试账本统计"""
        # 添加一些条目
        for i in range(5):
            vr = ValidationResult(is_valid=(i % 2 == 0),
                                metadata={"index": i})
            self.ledger.add_validation_result(vr)

        stats = self.ledger.get_ledger_stats()

        self.assertEqual(stats["total_entries"], 5)
        self.assertEqual(stats["current_batch_size"], 2)  # 5 % 3 = 2
        self.assertEqual(stats["batch_size_limit"], 3)
        self.assertGreaterEqual(stats["batches_committed"], 1)

    def test_blockchain_transaction_preparation(self):
        """测试区块链交易准备"""
        # 添加条目并提交批次
        for i in range(2):
            vr = ValidationResult(is_valid=True, metadata={"index": i})
            self.ledger.add_validation_result(vr)

        batch_id = self.ledger.force_commit_batch()
        transaction_data = self.ledger.prepare_blockchain_transaction(batch_id)

        self.assertIn("batch_id", transaction_data)
        self.assertIn("root_hash", transaction_data)
        self.assertIn("entry_count", transaction_data)
        self.assertIn("timestamp", transaction_data)
        self.assertIn("entries_hashes", transaction_data)

        self.assertEqual(transaction_data["entry_count"], 2)
        self.assertEqual(len(transaction_data["entries_hashes"]), 2)

    def test_validation_result_serialization(self):
        """测试验证结果序列化"""
        vr = ValidationResult(
            is_valid=False,
            errors=["error1", "error2"],
            warnings=["warning1"],
            metadata={"key": "value"},
            constitutional_hash="test_hash"
        )

        data = vr.to_dict()
        self.assertIn("is_valid", data)
        self.assertIn("errors", data)
        self.assertIn("warnings", data)
        self.assertIn("metadata", data)
        self.assertIn("constitutional_hash", data)
        self.assertIn("timestamp", data)

        self.assertEqual(data["is_valid"], False)
        self.assertEqual(data["errors"], ["error1", "error2"])
        self.assertEqual(data["warnings"], ["warning1"])


if __name__ == '__main__':
    unittest.main()