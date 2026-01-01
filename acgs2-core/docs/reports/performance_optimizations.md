# Performance Optimizations: Impact Scorer

This document details the optimizations applied to the `distilbert`-based impact scoring engine in ACGS-2.

## Model Evolution

| Model | Size (MB) | Accuracy (Relative) | Latency (ms) | Memory (GB) |
|-------|-----------|---------------------|--------------|-------------|
| BERT Base | 440 | 100% | 150-200 | ~1.2 |
| DistilBERT | 265 | 95% | 60-80 | ~0.6 |
| **DistilBERT ONNX (INT8)** | **65** | **93%** | **15-25** | **~0.2** |

## Enhancements

### 1. Model Quantization (INT8)
By utilizing `onnxruntime` and `Hugging Face Optimum`, the model weights were quantized from FP32 to INT8. This resulted in:
- **70% reduction** in model size.
- **2-4x speedup** on CPU-only environments.

### 2. DistilBERT Swap
Replacing the standard `bert-base-uncased` with `distilbert-base-uncased` provided a significant efficiency boost with minimal loss in semantic understanding. DistilBERT has 40% fewer parameters while retaining 97% of BERT's performance on downstream tasks.

### 3. ONNX Runtime Integration
The switch to ONNX Runtime allows for hardware-accelerated inference across multiple backends (CPU, CUDA, CoreML) without needing the full `torch` stack if only inference is required.

## Benchmarking Results

Benchmarks were conducted using `testing/benchmark_scorer.py` on a standard CPU node.

### CPU Inference (Threaded)
- **Baseline BERT**: 5.2 qps
- **DistilBERT (PyTorch)**: 12.8 qps
- **DistilBERT (ONNX)**: 45.1 qps (with 4 OMP threads)

## Reproduction Steps

```bash
# Install benchmark dependencies
pip install onnxruntime-tools numpy

# Run benchmark
python testing/benchmark_scorer.py --iterations 500
```
