import asyncio
import pytest
import time
from services.audit_service.core.audit_ledger import AuditLedger, ValidationResult

@pytest.fixture
async def ledger():
    """AuditLedger fixture"""
    l = AuditLedger(batch_size=3)
    await l.start()
    yield l
    await l.stop()

@pytest.mark.asyncio
class TestAsyncAuditLedger:
    """AsyncAuditLedger单元测试"""

    async def test_add_single_validation_result(self, ledger):
        """测试添加单个验证结果"""
        vr = ValidationResult(is_valid=True, metadata={"test": "data"})
        entry_hash = await ledger.add_validation_result(vr)

        assert entry_hash is not None
        
        # 异步处理需要一点时间，或者手动等待队列处理完成
        await ledger._queue.join()
        
        assert len(ledger.entries) == 1
        assert len(ledger.current_batch) == 1

        entry = ledger.entries[0]
        assert entry.validation_result == vr
        assert entry.hash == entry_hash

    async def test_batch_commitment(self, ledger):
        """测试批次提交"""
        # 添加足够条目触发批次提交
        for i in range(3):
            vr = ValidationResult(is_valid=True,
                                metadata={"index": i})
            await ledger.add_validation_result(vr)

        # 等待后台处理完所有任务
        await ledger._queue.join()

        # 检查批次是否已提交
        assert len(ledger.current_batch) == 0
        assert ledger.merkle_tree is not None

        # 检查所有条目都有批次ID
        for entry in ledger.entries:
            assert entry.batch_id is not None
            assert entry.merkle_proof is not None

    async def test_entry_verification(self, ledger):
        """测试条目验证"""
        # 添加条目并提交批次
        vr = ValidationResult(is_valid=True, metadata={"test": "verification"})
        entry_hash = await ledger.add_validation_result(vr)
        
        # 等待后台处理完添加任务
        await ledger._queue.join()
        
        # 强制提交批次
        batch_id = await ledger.force_commit_batch()

        # 获取条目和证明
        entry = ledger.entries[0]
        proof = entry.merkle_proof

        # 获取实际的merkle root hash用于验证
        root_hash = ledger.get_batch_root_hash(batch_id)
        assert root_hash is not None

        # 验证条目
        is_valid = await ledger.verify_entry(entry_hash, proof, root_hash)
        assert is_valid is True

    async def test_invalid_verification(self, ledger):
        """测试无效验证"""
        # 添加条目
        vr = ValidationResult(is_valid=True, metadata={"test": "invalid"})
        await ledger.add_validation_result(vr)
        
        # 等待处理
        await ledger._queue.join()
        
        batch_id = await ledger.force_commit_batch()

        entry = ledger.entries[0]
        root_hash = ledger.get_batch_root_hash(batch_id)

        # 使用错误的哈希验证
        wrong_hash = "wrong_hash"
        is_valid = await ledger.verify_entry(wrong_hash, entry.merkle_proof, root_hash)
        assert is_valid is False

        # 使用错误的根哈希验证
        wrong_root = "wrong_root_hash"
        is_valid = await ledger.verify_entry(entry.hash, entry.merkle_proof, wrong_root)
        assert is_valid is False

    async def test_get_entries_by_batch(self, ledger):
        """测试按批次获取条目"""
        # 添加多个批次的条目
        for batch in range(2):
            for i in range(2):
                vr = ValidationResult(is_valid=True,
                                    metadata={"batch": batch, "index": i})
                await ledger.add_validation_result(vr)
            
            # 等待处理
            await ledger._queue.join()
            await ledger.force_commit_batch()

        # 检查批次
        batch_ids = set(entry.batch_id for entry in ledger.entries if entry.batch_id)
        assert len(batch_ids) > 0

        # 获取特定批次的条目
        for batch_id in batch_ids:
            entries = await ledger.get_entries_by_batch(batch_id)
            assert len(entries) > 0
            for entry in entries:
                assert entry.batch_id == batch_id

    async def test_ledger_stats(self, ledger):
        """测试账本统计"""
        # 添加一些条目
        for i in range(5):
            vr = ValidationResult(is_valid=(i % 2 == 0),
                                metadata={"index": i})
            await ledger.add_validation_result(vr)

        # 等待处理完成
        await ledger._queue.join()
        
        # 强制提交剩余部分
        await ledger.force_commit_batch()

        stats = await ledger.get_ledger_stats()

        assert stats["total_entries"] == 5
        assert stats["current_batch_size"] == 0
        assert stats["batch_size_limit"] == 3
        assert stats["batches_committed"] >= 2

    async def test_blockchain_transaction_preparation(self, ledger):
        """测试区块链交易准备"""
        # 添加条目并提交批次
        for i in range(2):
            vr = ValidationResult(is_valid=True, metadata={"index": i})
            await ledger.add_validation_result(vr)

        # 等待处理
        await ledger._queue.join()
        
        batch_id = await ledger.force_commit_batch()
        transaction_data = await ledger.prepare_blockchain_transaction(batch_id)

        assert "batch_id" in transaction_data
        assert "root_hash" in transaction_data
        assert "entry_count" in transaction_data
        assert "timestamp" in transaction_data
        assert "entries_hashes" in transaction_data

        assert transaction_data["entry_count"] == 2
        assert len(transaction_data["entries_hashes"]) == 2