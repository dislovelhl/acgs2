import hashlib
import unittest

from services.audit_service.core.merkle_tree.merkle_tree import MerkleTree


class TestMerkleTree(unittest.TestCase):
    """Merkle Tree单元测试"""

    def test_empty_tree(self):
        """测试空树"""
        tree = MerkleTree()
        self.assertIsNone(tree.get_root_hash())
        self.assertEqual(tree.get_leaf_count(), 0)
        self.assertEqual(tree.get_tree_height(), 0)

    def test_single_leaf(self):
        """测试单叶子节点"""
        data = b"test data"
        tree = MerkleTree([data])
        expected_hash = hashlib.sha256(data).hexdigest()
        self.assertEqual(tree.get_root_hash(), expected_hash)
        self.assertEqual(tree.get_leaf_count(), 1)
        self.assertEqual(tree.get_tree_height(), 0)

    def test_multiple_leaves(self):
        """测试多叶子节点"""
        data_list = [b"data1", b"data2", b"data3", b"data4"]
        tree = MerkleTree(data_list)
        self.assertIsNotNone(tree.get_root_hash())
        self.assertEqual(tree.get_leaf_count(), 4)
        self.assertGreater(tree.get_tree_height(), 0)

    def test_proof_generation_and_verification(self):
        """测试证明生成和验证"""
        data_list = [b"data1", b"data2", b"data3", b"data4"]
        tree = MerkleTree(data_list)
        root_hash = tree.get_root_hash()

        # 测试第一个叶子节点的证明
        proof = tree.get_proof(0)
        self.assertTrue(len(proof) > 0)
        is_valid = tree.verify_proof(b"data1", proof, root_hash)
        self.assertTrue(is_valid)

        # 测试最后一个叶子节点的证明
        proof = tree.get_proof(3)
        self.assertTrue(len(proof) > 0)
        is_valid = tree.verify_proof(b"data4", proof, root_hash)
        self.assertTrue(is_valid)

    def test_invalid_proof(self):
        """测试无效证明"""
        data_list = [b"data1", b"data2", b"data3", b"data4"]
        tree = MerkleTree(data_list)
        root_hash = tree.get_root_hash()

        # 使用错误的叶子数据验证
        proof = tree.get_proof(0)
        is_valid = tree.verify_proof(b"wrong data", proof, root_hash)
        self.assertFalse(is_valid)

        # 使用错误的根哈希验证
        wrong_root = "wrong_hash"
        is_valid = tree.verify_proof(b"data1", proof, wrong_root)
        self.assertFalse(is_valid)

    def test_add_leaf(self):
        """测试添加叶子节点"""
        tree = MerkleTree([b"data1", b"data2"])
        original_root = tree.get_root_hash()
        original_count = tree.get_leaf_count()

        tree.add_leaf(b"data3")
        new_root = tree.get_root_hash()
        new_count = tree.get_leaf_count()

        # 根哈希应该改变
        self.assertNotEqual(original_root, new_root)
        # 叶子数量应该增加
        self.assertEqual(new_count, original_count + 1)

        # 验证新添加的叶子
        proof = tree.get_proof(2)
        is_valid = tree.verify_proof(b"data3", proof, new_root)
        self.assertTrue(is_valid)

    def test_large_tree(self):
        """测试大树"""
        # 创建1000个叶子节点
        data_list = [f"data{i}".encode() for i in range(1000)]
        tree = MerkleTree(data_list)

        self.assertEqual(tree.get_leaf_count(), 1000)
        self.assertIsNotNone(tree.get_root_hash())

        # 验证几个随机叶子
        test_indices = [0, 100, 500, 999]
        for idx in test_indices:
            proof = tree.get_proof(idx)
            is_valid = tree.verify_proof(data_list[idx], proof, tree.get_root_hash())
            self.assertTrue(is_valid)

    def test_tree_height_calculation(self):
        """测试树高度计算"""
        # 1个叶子：高度0
        tree = MerkleTree([b"data"])
        self.assertEqual(tree.get_tree_height(), 0)

        # 2个叶子：高度1
        tree = MerkleTree([b"data1", b"data2"])
        self.assertEqual(tree.get_tree_height(), 1)

        # 4个叶子：高度2
        tree = MerkleTree([b"data1", b"data2", b"data3", b"data4"])
        self.assertEqual(tree.get_tree_height(), 2)

        # 8个叶子：高度3
        data_list = [f"data{i}".encode() for i in range(8)]
        tree = MerkleTree(data_list)
        self.assertEqual(tree.get_tree_height(), 3)


if __name__ == "__main__":
    unittest.main()
