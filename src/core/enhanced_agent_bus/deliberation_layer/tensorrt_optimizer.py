"""
ACGS-2 TensorRT Optimizer for DistilBERT Inference
Constitutional Hash: cdd01ef066bc6cf2

Optimizes DistilBERT model inference using NVIDIA TensorRT for GPU acceleration.
Based on benchmark results showing 25.24ms P99 latency with 798.6% CPU usage.

Target: Reduce P99 latency from 25ms to <5ms using GPU acceleration.

Usage:
    from deliberation_layer.tensorrt_optimizer import TensorRTOptimizer

    optimizer = TensorRTOptimizer("distilbert-base-uncased")
    optimizer.export_onnx()  # First export to ONNX
    optimizer.convert_to_tensorrt()  # Then convert to TensorRT

    # Use optimized inference
    embeddings = optimizer.infer(text)
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)

# TensorRT availability check
TENSORRT_AVAILABLE = False
ONNX_AVAILABLE = False
TORCH_AVAILABLE = False

try:
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    pass

try:
    import onnx
    import onnxruntime as ort

    ONNX_AVAILABLE = True
except ImportError:
    pass

try:
    import tensorrt as trt

    TENSORRT_AVAILABLE = True
except ImportError:
    pass


class TensorRTOptimizer:
    """
    Converts PyTorch DistilBERT to TensorRT for GPU-accelerated inference.

    Optimization Pipeline:
    1. PyTorch Model → ONNX Export
    2. ONNX → TensorRT Engine (with FP16 optimization)
    3. TensorRT Engine → Low-latency inference

    Expected Performance Improvement:
    - Current P99: 25.24ms (CPU)
    - Target P99: <5ms (GPU with TensorRT)
    - Improvement: 5x+ speedup
    """

    DEFAULT_MODEL_DIR = Path(__file__).parent / "optimized_models"

    def __init__(
        self,
        model_name: str = "distilbert-base-uncased",
        max_seq_length: int = 128,
        use_fp16: bool = True,
        cache_dir: Optional[Path] = None,
    ):
        """
        Initialize TensorRT optimizer.

        Args:
            model_name: HuggingFace model name
            max_seq_length: Maximum sequence length for inference
            use_fp16: Use FP16 precision for faster inference
            cache_dir: Directory to cache optimized models
        """
        self.model_name = model_name
        self.max_seq_length = max_seq_length
        self.use_fp16 = use_fp16
        self.cache_dir = cache_dir or self.DEFAULT_MODEL_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Model paths
        self.model_id = model_name.replace("/", "_").replace("-", "_")
        self.onnx_path = self.cache_dir / f"{self.model_id}.onnx"
        self.trt_path = self.cache_dir / f"{self.model_id}.trt"

        # Runtime components
        self._tokenizer = None
        self._torch_model = None
        self._onnx_session = None
        self._trt_engine = None
        self._trt_context = None

        self._optimization_status = {
            "onnx_exported": self.onnx_path.exists(),
            "tensorrt_ready": self.trt_path.exists(),
            "active_backend": "none",
        }

    @property
    def status(self) -> Dict[str, Any]:
        """Return current optimization status."""
        return {
            **self._optimization_status,
            "torch_available": TORCH_AVAILABLE,
            "onnx_available": ONNX_AVAILABLE,
            "tensorrt_available": TENSORRT_AVAILABLE,
            "model_name": self.model_name,
            "max_seq_length": self.max_seq_length,
            "use_fp16": self.use_fp16,
        }

    def _load_tokenizer(self):
        """Load HuggingFace tokenizer."""
        if self._tokenizer is None:
            from transformers import AutoTokenizer

            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        return self._tokenizer

    def _load_torch_model(self):
        """Load PyTorch model for export."""
        if self._torch_model is None:
            if not TORCH_AVAILABLE:
                raise RuntimeError("PyTorch not available for model export")

            from transformers import AutoModel

            self._torch_model = AutoModel.from_pretrained(self.model_name)
            self._torch_model.eval()

            # Move to GPU if available
            if torch.cuda.is_available():
                self._torch_model = self._torch_model.cuda()
                logger.info("Model loaded on GPU")
            else:
                logger.info("Model loaded on CPU (GPU not available)")

        return self._torch_model

    def export_onnx(self, force: bool = False) -> Path:
        """
        Export PyTorch model to ONNX format.

        Args:
            force: Force re-export even if ONNX file exists

        Returns:
            Path to exported ONNX model
        """
        if self.onnx_path.exists() and not force:
            logger.info(f"ONNX model already exists: {self.onnx_path}")
            self._optimization_status["onnx_exported"] = True
            return self.onnx_path

        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch required for ONNX export")

        logger.info(f"Exporting {self.model_name} to ONNX...")

        tokenizer = self._load_tokenizer()
        model = self._load_torch_model()

        # Create dummy input for tracing
        dummy_text = "This is a sample input for model tracing."
        dummy_inputs = tokenizer(
            dummy_text,
            padding="max_length",
            truncation=True,
            max_length=self.max_seq_length,
            return_tensors="pt",
        )

        if torch.cuda.is_available():
            dummy_inputs = {k: v.cuda() for k, v in dummy_inputs.items()}

        # Export to ONNX
        input_names = ["input_ids", "attention_mask"]
        output_names = ["last_hidden_state"]

        dynamic_axes = {
            "input_ids": {0: "batch_size"},
            "attention_mask": {0: "batch_size"},
            "last_hidden_state": {0: "batch_size"},
        }

        torch.onnx.export(
            model,
            (dummy_inputs["input_ids"], dummy_inputs["attention_mask"]),
            str(self.onnx_path),
            input_names=input_names,
            output_names=output_names,
            dynamic_axes=dynamic_axes,
            opset_version=14,
            do_constant_folding=True,
        )

        logger.info(f"ONNX model exported to: {self.onnx_path}")
        self._optimization_status["onnx_exported"] = True

        # Validate ONNX model
        if ONNX_AVAILABLE:
            import onnx

            onnx_model = onnx.load(str(self.onnx_path))
            onnx.checker.check_model(onnx_model)
            logger.info("ONNX model validation passed")

        return self.onnx_path

    def convert_to_tensorrt(self, force: bool = False) -> Optional[Path]:
        """
        Convert ONNX model to TensorRT engine.

        Args:
            force: Force re-conversion even if TRT file exists

        Returns:
            Path to TensorRT engine, or None if TRT not available
        """
        if not TENSORRT_AVAILABLE:
            logger.warning("TensorRT not available. Install tensorrt package.")
            return None

        if self.trt_path.exists() and not force:
            logger.info(f"TensorRT engine already exists: {self.trt_path}")
            self._optimization_status["tensorrt_ready"] = True
            return self.trt_path

        if not self.onnx_path.exists():
            logger.info("ONNX model not found. Exporting first...")
            self.export_onnx()

        logger.info("Converting ONNX to TensorRT...")

        # Create TensorRT builder and network
        TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
        builder = trt.Builder(TRT_LOGGER)
        network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
        parser = trt.OnnxParser(network, TRT_LOGGER)

        # Parse ONNX model
        with open(self.onnx_path, "rb") as f:
            if not parser.parse(f.read()):
                for i in range(parser.num_errors):
                    logger.error(f"ONNX parse error: {parser.get_error(i)}")
                raise RuntimeError("Failed to parse ONNX model")

        # Configure builder
        config = builder.create_builder_config()
        config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, 1 << 30)  # 1GB

        if self.use_fp16 and builder.platform_has_fast_fp16:
            config.set_flag(trt.BuilderFlag.FP16)
            logger.info("FP16 optimization enabled")

        # Set optimization profile for dynamic shapes
        profile = builder.create_optimization_profile()
        profile.set_shape(
            "input_ids",
            (1, 1),  # min
            (4, self.max_seq_length // 2),  # opt
            (8, self.max_seq_length),  # max
        )
        profile.set_shape(
            "attention_mask",
            (1, 1),
            (4, self.max_seq_length // 2),
            (8, self.max_seq_length),
        )
        config.add_optimization_profile(profile)

        # Build TensorRT engine
        logger.info("Building TensorRT engine (this may take a few minutes)...")
        serialized_engine = builder.build_serialized_network(network, config)

        if serialized_engine is None:
            raise RuntimeError("Failed to build TensorRT engine")

        # Save engine
        with open(self.trt_path, "wb") as f:
            f.write(serialized_engine)

        logger.info(f"TensorRT engine saved to: {self.trt_path}")
        self._optimization_status["tensorrt_ready"] = True

        return self.trt_path

    def load_tensorrt_engine(self) -> bool:
        """
        Load TensorRT engine for inference.

        Returns:
            True if engine loaded successfully
        """
        if not TENSORRT_AVAILABLE:
            logger.warning("TensorRT not available")
            return False

        if not self.trt_path.exists():
            logger.warning(f"TensorRT engine not found: {self.trt_path}")
            return False

        TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
        runtime = trt.Runtime(TRT_LOGGER)

        with open(self.trt_path, "rb") as f:
            self._trt_engine = runtime.deserialize_cuda_engine(f.read())

        if self._trt_engine is None:
            logger.error("Failed to load TensorRT engine")
            return False

        self._trt_context = self._trt_engine.create_execution_context()
        self._optimization_status["active_backend"] = "tensorrt"
        logger.info("TensorRT engine loaded successfully")

        return True

    def load_onnx_runtime(self) -> bool:
        """
        Load ONNX Runtime as fallback when TensorRT not available.

        Returns:
            True if ONNX session loaded successfully
        """
        if not ONNX_AVAILABLE:
            logger.warning("ONNX Runtime not available")
            return False

        if not self.onnx_path.exists():
            logger.warning(f"ONNX model not found: {self.onnx_path}")
            return False

        # Configure ONNX Runtime with GPU if available
        providers = []
        if "CUDAExecutionProvider" in ort.get_available_providers():
            providers.append("CUDAExecutionProvider")
            logger.info("Using CUDA execution provider")
        providers.append("CPUExecutionProvider")

        self._onnx_session = ort.InferenceSession(
            str(self.onnx_path),
            providers=providers,
        )

        self._optimization_status["active_backend"] = "onnxruntime"
        logger.info("ONNX Runtime session loaded")

        return True

    def infer(self, text: str) -> np.ndarray:
        """
        Run inference on text input.

        Args:
            text: Input text to process

        Returns:
            Embeddings as numpy array
        """
        tokenizer = self._load_tokenizer()
        inputs = tokenizer(
            text,
            padding="max_length",
            truncation=True,
            max_length=self.max_seq_length,
            return_tensors="np",
        )

        # Select inference backend
        if self._trt_context is not None:
            return self._infer_tensorrt(inputs)
        elif self._onnx_session is not None:
            return self._infer_onnx(inputs)
        else:
            return self._infer_torch(inputs)

    def _infer_tensorrt(self, inputs: Dict[str, np.ndarray]) -> np.ndarray:
        """TensorRT inference implementation."""

        # Allocate buffers and run inference
        # (Implementation depends on specific TensorRT version)
        raise NotImplementedError("TensorRT inference requires CUDA setup")

    def _infer_onnx(self, inputs: Dict[str, np.ndarray]) -> np.ndarray:
        """ONNX Runtime inference."""
        input_feed = {
            "input_ids": inputs["input_ids"],
            "attention_mask": inputs["attention_mask"],
        }

        outputs = self._onnx_session.run(None, input_feed)

        # Return mean pooled embeddings
        last_hidden_state = outputs[0]
        attention_mask = inputs["attention_mask"]

        # Mean pooling
        input_mask_expanded = np.broadcast_to(
            attention_mask[:, :, np.newaxis], last_hidden_state.shape
        ).astype(np.float32)

        sum_embeddings = np.sum(last_hidden_state * input_mask_expanded, axis=1)
        sum_mask = np.clip(input_mask_expanded.sum(axis=1), a_min=1e-9, a_max=None)

        return sum_embeddings / sum_mask

    def _infer_torch(self, inputs: Dict[str, np.ndarray]) -> np.ndarray:
        """Fallback PyTorch inference."""
        model = self._load_torch_model()

        input_ids = torch.from_numpy(inputs["input_ids"])
        attention_mask = torch.from_numpy(inputs["attention_mask"])

        if torch.cuda.is_available():
            input_ids = input_ids.cuda()
            attention_mask = attention_mask.cuda()

        with torch.no_grad():
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)

        # Mean pooling
        last_hidden_state = outputs.last_hidden_state
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()

        sum_embeddings = torch.sum(last_hidden_state * input_mask_expanded, dim=1)
        sum_mask = torch.clamp(input_mask_expanded.sum(dim=1), min=1e-9)

        embeddings = sum_embeddings / sum_mask

        return embeddings.cpu().numpy()

    def benchmark(self, num_samples: int = 100) -> Dict[str, Any]:
        """
        Benchmark current inference backend.

        Args:
            num_samples: Number of samples to benchmark

        Returns:
            Benchmark results with latency statistics
        """
        import time

        sample_texts = [
            "Critical security breach detected in blockchain consensus layer",
            "Standard health check request",
            "Unauthorized financial transfer attempt blocked",
            "Performance metrics indicate potential anomaly",
        ]

        latencies = []

        # Warmup
        for _ in range(10):
            self.infer(sample_texts[0])

        # Benchmark
        for i in range(num_samples):
            text = sample_texts[i % len(sample_texts)]

            start = time.perf_counter()
            _ = self.infer(text)
            end = time.perf_counter()

            latencies.append((end - start) * 1000)  # ms

        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)

        return {
            "backend": self._optimization_status["active_backend"],
            "num_samples": n,
            "latency_p50_ms": sorted_latencies[int(n * 0.50)],
            "latency_p95_ms": sorted_latencies[int(n * 0.95)],
            "latency_p99_ms": sorted_latencies[int(n * 0.99)],
            "latency_mean_ms": sum(latencies) / n,
            "latency_min_ms": min(latencies),
            "latency_max_ms": max(latencies),
        }


def get_optimization_status() -> Dict[str, Any]:
    """Get current TensorRT optimization status."""
    optimizer = TensorRTOptimizer()
    return optimizer.status


def optimize_distilbert(force: bool = False) -> Dict[str, Any]:
    """
    One-shot optimization of DistilBERT for production use.

    Args:
        force: Force re-optimization

    Returns:
        Optimization status and paths
    """
    optimizer = TensorRTOptimizer("distilbert-base-uncased")

    results = {
        "initial_status": optimizer.status.copy(),
        "steps_completed": [],
    }

    # Step 1: Export to ONNX
    try:
        onnx_path = optimizer.export_onnx(force=force)
        results["steps_completed"].append("onnx_export")
        results["onnx_path"] = str(onnx_path)
    except Exception as e:
        results["onnx_error"] = str(e)
        return results

    # Step 2: Convert to TensorRT (if available)
    if TENSORRT_AVAILABLE:
        try:
            trt_path = optimizer.convert_to_tensorrt(force=force)
            if trt_path:
                results["steps_completed"].append("tensorrt_convert")
                results["tensorrt_path"] = str(trt_path)
        except Exception as e:
            results["tensorrt_error"] = str(e)
    else:
        results["tensorrt_skipped"] = "TensorRT not available"

    # Step 3: Load best available backend and benchmark
    if optimizer.load_tensorrt_engine():
        results["active_backend"] = "tensorrt"
    elif optimizer.load_onnx_runtime():
        results["active_backend"] = "onnxruntime"
    else:
        results["active_backend"] = "pytorch"

    # Benchmark
    try:
        results["benchmark"] = optimizer.benchmark(num_samples=50)
        results["steps_completed"].append("benchmark")
    except Exception as e:
        results["benchmark_error"] = str(e)

    results["final_status"] = optimizer.status.copy()

    return results
