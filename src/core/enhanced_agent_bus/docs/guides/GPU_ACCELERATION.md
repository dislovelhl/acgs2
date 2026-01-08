# ACGS-2 GPU Acceleration for DistilBERT Inference

**Constitutional Hash:** cdd01ef066bc6cf2
**Status:** Ready for GPU Deployment
**Date:** 2025-12-29

## Executive Summary

Benchmark analysis identified DistilBERT inference as **compute-bound** with 798.6% CPU utilization and 25.24ms P99 latency. GPU acceleration via NVIDIA TensorRT is **strongly recommended** to achieve the <5ms target.

## Benchmark Results

### Current Performance (CPU)

| Metric | PyTorch | ONNX Runtime | Target |
|--------|---------|--------------|--------|
| P50 Latency | 13.94ms | 26.72ms | <5ms |
| P95 Latency | 22.79ms | 27.57ms | <5ms |
| P99 Latency | 25.24ms | 39.15ms | <5ms |
| CPU Usage | 798.6% | N/A | - |
| Bottleneck | **Compute-bound** | **Compute-bound** | - |

### Expected GPU Performance

With NVIDIA TensorRT and FP16 optimization:

| Metric | Expected | Improvement |
|--------|----------|-------------|
| P99 Latency | 2-5ms | 5-10x faster |
| Throughput | 500+ RPS | 3-5x higher |
| GPU Utilization | 30-60% | Efficient |

## Optimization Pipeline

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   PyTorch   │ --> │     ONNX     │ --> │  TensorRT    │
│  DistilBERT │     │   Export     │     │   Engine     │
│  (25ms P99) │     │  (exported)  │     │  (<5ms P99)  │
└─────────────┘     └──────────────┘     └──────────────┘
```

### Step 1: ONNX Export ✅ Complete

```bash
# Already exported to:
# src/core/enhanced_agent_bus/deliberation_layer/optimized_models/distilbert_base_uncased.onnx
```

### Step 2: TensorRT Conversion (GPU Required)

```python
from deliberation_layer.tensorrt_optimizer import optimize_distilbert

# On GPU server:
results = optimize_distilbert()
# Creates: optimized_models/distilbert_base_uncased.trt
```

### Step 3: Production Deployment

```python
from deliberation_layer.tensorrt_optimizer import TensorRTOptimizer

optimizer = TensorRTOptimizer("distilbert-base-uncased")
optimizer.load_tensorrt_engine()  # or load_onnx_runtime() for GPU without TRT

embeddings = optimizer.infer(text)
```

## Files Created

| File | Purpose |
|------|---------|
| `profiling/__init__.py` | Module exports |
| `profiling/model_profiler.py` | GPU decision analyzer |
| `profiling/benchmark_gpu_decision.py` | Benchmark script |
| `deliberation_layer/tensorrt_optimizer.py` | ONNX/TensorRT optimizer |
| `deliberation_layer/optimized_models/distilbert_base_uncased.onnx` | Optimized model |

## GPU Infrastructure Requirements

### Minimum Requirements

- NVIDIA GPU with Compute Capability 7.0+ (V100, T4, A10, A100)
- CUDA 11.8+ and cuDNN 8.6+
- TensorRT 8.5+ (recommended 10.x)
- 8GB+ GPU memory

### Recommended Stack

```yaml
# Production deployment
nvidia/cuda:12.1-cudnn8-runtime-ubuntu22.04

packages:
  - onnxruntime-gpu>=1.17.0
  - tensorrt>=10.0.0  # For TensorRT optimization
  - torch>=2.0.0+cu121
```

## Integration with Impact Scorer

The `impact_scorer.py` has been instrumented with profiling. To enable GPU inference:

```python
# In impact_scorer.py, replace:
from transformers import AutoModel

# With:
from .tensorrt_optimizer import TensorRTOptimizer

class ImpactScorer:
    def __init__(self, ...):
        self.optimizer = TensorRTOptimizer(model_name)
        if self.optimizer.load_tensorrt_engine():
            self._backend = "tensorrt"
        elif self.optimizer.load_onnx_runtime():
            self._backend = "onnxruntime-gpu"
        else:
            # Fallback to PyTorch
            self.model = AutoModel.from_pretrained(model_name)
            self._backend = "pytorch"
```

## Performance Monitoring

### Profiling Commands

```bash
# Run GPU decision benchmark
cd src/core
python -m enhanced_agent_bus.profiling.benchmark_gpu_decision --samples 200

# Check optimization status
python -c "from enhanced_agent_bus.deliberation_layer.tensorrt_optimizer import get_optimization_status; print(get_optimization_status())"
```

### Prometheus Metrics

The profiler exports:
- `acgs2_model_inference_latency_seconds` (histogram)
- `acgs2_model_inference_total` (counter)
- `acgs2_model_cpu_percent` (gauge)

## Decision Matrix

| Model | Current P99 | Bottleneck | GPU Recommendation |
|-------|-------------|------------|-------------------|
| DistilBERT (Impact Scorer) | 25.24ms | Compute-bound | ✅ **YES - TensorRT** |
| RandomForest (Anomaly) | <1ms | I/O-bound | ❌ No benefit |
| XGBoost (Compliance) | <1ms | I/O-bound | ❌ No benefit |

## Next Steps

1. **Deploy to GPU Server**
   - Install CUDA runtime and TensorRT
   - Run `optimize_distilbert()` to create TensorRT engine
   - Benchmark with GPU acceleration

2. **Integrate GPU Inference**
   - Update `ImpactScorer` to use TensorRT backend
   - Add fallback chain: TensorRT → ONNX-GPU → ONNX-CPU → PyTorch

3. **Monitor Performance**
   - Set up Prometheus dashboards for GPU metrics
   - Alert on P99 > 5ms threshold

## Constitutional Compliance

All GPU acceleration code maintains ACGS-2 constitutional hash verification:
```
Constitutional Hash: cdd01ef066bc6cf2
```

GPU optimization does not affect constitutional validation logic.
