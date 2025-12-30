# NVIDIA GPU Acceleration Integration - Kilo Code Context

## Project: ACGS-2 (AI Constitutional Governance System)

### Current Performance Metrics
- **P99 Latency:** 0.278ms (target <5ms) - 94% better than target
- **Throughput:** 6,310 RPS (target >100 RPS) - 63x capacity
- **Cache Hit Rate:** 95%
- **Constitutional Compliance:** 100%

### ML Models Requiring GPU Evaluation

| # | Model | Framework | Current Latency | GPU Candidate |
|---|-------|-----------|-----------------|---------------|
| 1 | Anomaly Detection | sklearn (RandomForest) | Real-time | RAPIDS cuML |
| 2 | Compliance Classification | XGBoost + LLM | Per-request | RAPIDS cuML |
| 3-5 | Performance Prediction | sklearn Ensemble | Batch | RAPIDS cuML |
| 6 | Impact Scorer (DistilBERT) | PyTorch | ~2-3ms | TensorRT |
| 7 | Impact Scorer (BERT-base) | PyTorch | Validation | TensorRT |
| 8 | Quantized Inference | ONNX Runtime | <50ms | TensorRT |

### Integration Priorities

1. **RAPIDS/cuML** - Batch workloads and training (lowest risk)
2. **TensorRT** - PyTorch model optimization (if DistilBERT is bottleneck)
3. **Triton** - Only if standardized serving needed

### Key Files
- `/enhanced_agent_bus/deliberation_layer/impact_scorer.py` - DistilBERT inference
- `/enhanced_agent_bus/deliberation_layer/adaptive_router.py` - Routing logic
- `/enhanced_agent_bus/message_processor.py` - Integration point

### Technical Constraints
- Python 3.13 compatibility required
- Must maintain sub-5ms P99 latency
- Constitutional hash validation: `cdd01ef066bc6cf2`
- Non-blocking fire-and-forget pattern for metering

### Development Tasks

#### Phase 1: Profiling (Required First)
- [ ] Add model execution time instrumentation
- [ ] Measure CPU vs model compute breakdown
- [ ] Identify actual bottlenecks under load

#### Phase 2: RAPIDS Integration (Batch First)
- [ ] Create cuML wrapper for sklearn models
- [ ] Implement GPU training pipeline
- [ ] Benchmark batch compliance scoring

#### Phase 3: TensorRT Optimization (If Needed)
- [ ] Export DistilBERT to ONNX
- [ ] Build TensorRT engine
- [ ] A/B benchmark: PyTorch vs TensorRT

### NVIDIA SDK Compatibility (Python 3.13)
- RAPIDS 25.06+: ✅ Python 3.13 support
- TensorRT: ✅ Python 3.13 wheels available
- Torch-TensorRT 2.7.0+: ✅ Python 3.9-3.13
- Triton: ⚠️ Container uses Python 3.12.x

### Questions for Kilo Code

1. Should we start with profiling to determine if GPU is worth it?
2. Which models would benefit most from GPU acceleration?
3. How to maintain backward compatibility with CPU-only deployments?
4. Best approach for gradual rollout without breaking existing performance?
