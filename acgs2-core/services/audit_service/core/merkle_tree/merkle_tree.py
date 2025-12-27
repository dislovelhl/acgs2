import hashlib
from typing import List, Optional, Tuple


class MerkleTree:
    """Merkle Tree实现，用于批量验证"""

    def __init__(self, data_list: Optional[List[bytes]] = None):
        self._original_data: List[bytes] = []
        self.leaves: List[str] = []
        self.tree: List[List[str]] = []
        self.root: Optional[str] = None

        if data_list:
            self.build_tree(data_list)

    def build_tree(self, data_list: List[bytes]) -> None:
        """构建Merkle Tree"""
        self._original_data = data_list[:]
        
        if not data_list:
            return

        # 创建叶子节点哈希
        self.leaves = [hashlib.sha256(data).hexdigest() for data in data_list]

        if len(self.leaves) == 1:
            self.root = self.leaves[0]
            self.tree = [self.leaves]
            return

        # 构建树结构
        self.tree = [self.leaves[:]]  # 第一层是叶子
        current_level = self.leaves[:]

        while len(current_level) > 1:
            next_level: List[str] = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                # 如果是奇数个节点，最后一个节点复制自己
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                combined = left + right
                parent_hash = hashlib.sha256(combined.encode()).hexdigest()
                next_level.append(parent_hash)

            self.tree.append(next_level)
            current_level = next_level

        self.root = current_level[0] if current_level else None

    def get_root_hash(self) -> Optional[str]:
        """获取根哈希"""
        return self.root

    def get_proof(self, index: int) -> List[Tuple[str, bool]]:
        """
        生成证明路径
        返回：[(sibling_hash, is_left), ...]
        """
        if not self.tree or index >= len(self.leaves):
            return []

        proof: List[Tuple[str, bool]] = []
        current_index = index

        for level_idx, level in enumerate(self.tree[:-1]):  # 不包括根层
            sibling_index = current_index ^ 1  # 切换左右兄弟
            
            # 处理边界情况：如果是奇数个节点且是最后一个，兄弟是自己
            if sibling_index >= len(level):
                sibling_index = current_index  # 使用自己作为兄弟
            
            sibling_hash = level[sibling_index]
            is_left = current_index % 2 == 0
            proof.append((sibling_hash, is_left))
            current_index //= 2

        return proof

    def verify_proof(self, leaf_data: bytes,
                    proof: List[Tuple[str, bool]],
                    root_hash: str) -> bool:
        """
        验证证明路径
        """
        current_hash = hashlib.sha256(leaf_data).hexdigest()

        for sibling_hash, is_left in proof:
            if is_left:
                # 当前节点是左子节点
                combined = current_hash + sibling_hash
            else:
                # 当前节点是右子节点
                combined = sibling_hash + current_hash
            current_hash = hashlib.sha256(combined.encode()).hexdigest()

        return current_hash == root_hash

    def add_leaf(self, data: bytes) -> None:
        """增量添加新的叶子节点，避免全量重建"""
        self._original_data.append(data)
        new_leaf_hash = hashlib.sha256(data).hexdigest()
        self.leaves.append(new_leaf_hash)
        
        if not self.tree:
            self.tree = [[new_leaf_hash]]
            self.root = new_leaf_hash
            return

        # 更新树结构
        self.tree[0] = self.leaves[:]
        current_hash = new_leaf_hash
        
        for i in range(len(self.tree) - 1):
            level = self.tree[i]
            next_level = self.tree[i+1]
            
            # 计算父节点索引
            parent_idx = (len(level) - 1) // 2
            
            if len(level) % 2 == 0:
                # 如果当前层是偶数个节点，说明新加入的是右子节点
                left = level[len(level) - 2]
                right = current_hash
            else:
                # 如果当前层是奇数个节点，说明新加入的是左子节点（或者是唯一的节点）
                left = current_hash
                right = current_hash # 复制自己
            
            combined = left + right
            parent_hash = hashlib.sha256(combined.encode()).hexdigest()
            
            if parent_idx < len(next_level):
                next_level[parent_idx] = parent_hash
            else:
                next_level.append(parent_hash)
            
            current_hash = parent_hash
            
        # 如果根层节点数增加，需要增加一层
        if len(self.tree[-1]) > 1:
            last_level = self.tree[-1]
            left = last_level[0]
            right = last_level[1] if len(last_level) > 1 else left
            combined = left + right
            new_root = hashlib.sha256(combined.encode()).hexdigest()
            self.tree.append([new_root])
            self.root = new_root
        else:
            self.root = self.tree[-1][0]

    def _rebuild_from_data(self) -> None:
        """从原始数据重建树"""
        self.build_tree(self._original_data)

    def get_tree_height(self) -> int:
        """获取树的高度"""
        return len(self.tree) - 1 if self.tree else 0

    def get_leaf_count(self) -> int:
        """获取叶子节点数量"""
        return len(self.leaves)
