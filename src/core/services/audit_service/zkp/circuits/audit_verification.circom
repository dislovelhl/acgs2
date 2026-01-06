pragma circom 2.1.0;

/**
 * 审计验证零知识证明电路
 *
 * 功能：
 * - 证明审计数据存在于Merkle Tree中
 * - 验证数据完整性而不透露具体内容
 * - 支持范围证明（数据在有效范围内）
 */

include "circomlib/poseidon.circom";
include "circomlib/comparators.circom";
include "circomlib/merkleTree.circom";

// Merkle Tree验证组件
template MerkleProof(levels) {
    signal input leaf;
    signal input root;
    signal input pathElements[levels];
    signal input pathIndices[levels];

    component hashers[levels];
    component selectors[levels];

    for (var i = 0; i < levels; i++) {
        selectors[i] = Selector();
        selectors[i].in[0] <== pathElements[i];
        selectors[i].in[1] <== i == 0 ? leaf : hashers[i-1].out;
        selectors[i].select <== pathIndices[i];

        hashers[i] = Poseidon(2);
        hashers[i].inputs[0] <== selectors[i].out[0];
        hashers[i].inputs[1] <== selectors[i].out[1];
    }

    root === hashers[levels-1].out;
}

// 审计数据验证电路
template AuditVerification(treeLevels) {
    // 公共输入
    signal input merkleRoot;        // Merkle Tree根哈希
    signal input expectedHash;      // 期望的数据哈希
    signal input minValue;          // 最小允许值
    signal input maxValue;          // 最大允许值

    // 私有输入
    signal input dataValue;         // 实际数据值
    signal input pathElements[treeLevels];  // Merkle证明路径
    signal input pathIndices[treeLevels];   // 路径索引

    // 中间信号
    signal computedHash;

    // 步骤1: 计算数据哈希
    component hasher = Poseidon(1);
    hasher.inputs[0] <== dataValue;
    computedHash <== hasher.out;

    // 步骤2: 验证哈希匹配
    computedHash === expectedHash;

    // 步骤3: 验证数据在有效范围内
    component rangeCheck = RangeCheck(treeLevels + 1);
    rangeCheck.in <== dataValue;
    rangeCheck.min <== minValue;
    rangeCheck.max <== maxValue;

    // 步骤4: 验证Merkle证明
    component merkleProof = MerkleProof(treeLevels);
    merkleProof.leaf <== computedHash;
    merkleProof.root <== merkleRoot;

    for (var i = 0; i < treeLevels; i++) {
        merkleProof.pathElements[i] <== pathElements[i];
        merkleProof.pathIndices[i] <== pathIndices[i];
    }
}

// 范围检查组件
template RangeCheck(bits) {
    signal input in;
    signal input min;
    signal input max;

    // 检查 in >= min
    component minCheck = GreaterEqThan(bits);
    minCheck.in[0] <== in;
    minCheck.in[1] <== min;
    minCheck.out === 1;

    // 检查 in <= max
    component maxCheck = LessEqThan(bits);
    maxCheck.in[0] <== in;
    maxCheck.in[1] <== max;
    maxCheck.out === 1;
}

// 批量审计验证电路
template BatchAuditVerification(treeLevels, batchSize) {
    // 公共输入
    signal input merkleRoot;
    signal input expectedHashes[batchSize];
    signal input minValues[batchSize];
    signal input maxValues[batchSize];

    // 私有输入
    signal input dataValues[batchSize];
    signal input pathElements[batchSize][treeLevels];
    signal input pathIndices[batchSize][treeLevels];

    component verifiers[batchSize];

    for (var i = 0; i < batchSize; i++) {
        verifiers[i] = AuditVerification(treeLevels);
        verifiers[i].merkleRoot <== merkleRoot;
        verifiers[i].expectedHash <== expectedHashes[i];
        verifiers[i].minValue <== minValues[i];
        verifiers[i].maxValue <== maxValues[i];
        verifiers[i].dataValue <== dataValues[i];

        for (var j = 0; j < treeLevels; j++) {
            verifiers[i].pathElements[j] <== pathElements[i][j];
            verifiers[i].pathIndices[j] <== pathIndices[i][j];
        }
    }
}

// 主电路 - 单个审计验证
component main {public [merkleRoot, expectedHash, minValue, maxValue]} = AuditVerification(10);

// 批量验证电路（可选）
// component main {public [merkleRoot]} = BatchAuditVerification(10, 100);
