"""
PAG-QEC: Predictive AI-Guided Quantum Error Correction Framework
Constitutional Hash: cdd01ef066bc6cf2

A comprehensive quantum error correction research framework implementing:
- Neural decoders for 3-qubit and surface codes
- Speculative execution for nanosecond-latency decoding
- MWPM baseline for comparison
- Curriculum training for surface codes
- ASCII visualization utilities

Modules:
- pag_qec_framework: Core neural decoder and speculative execution
- surface_code_extension: Surface code support (distance 3, 5, 7+)
- visualization: ASCII visualization for debugging and analysis

Usage:
    from quantum_research import (
        NeuralDecoder,
        ThreeQubitCodeEnvironment,
        SpeculativeExecutionEngine,
        SurfaceCodeNeuralDecoder,
        MWPMDecoder,
    )

Author: ACGS-2 Quantum Research Team
Based on 2025 breakthroughs from Google, IBM, and academic research.
"""

__version__ = "1.0.0"
__author__ = "ACGS-2 Quantum Research"
__constitutional_hash__ = "cdd01ef066bc6cf2"


# Lazy imports to avoid heavy dependencies at import time
def __getattr__(name):
    """Lazy import of submodules."""
    if name == "NeuralDecoder":
        from .pag_qec_framework import NeuralDecoder

        return NeuralDecoder
    elif name == "DecoderEnsemble":
        from .pag_qec_framework import DecoderEnsemble

        return DecoderEnsemble
    elif name == "ThreeQubitCodeEnvironment":
        from .pag_qec_framework import ThreeQubitCodeEnvironment

        return ThreeQubitCodeEnvironment
    elif name == "DecoderTrainer":
        from .pag_qec_framework import DecoderTrainer

        return DecoderTrainer
    elif name == "SpeculativeExecutionEngine":
        from .pag_qec_framework import SpeculativeExecutionEngine

        return SpeculativeExecutionEngine
    elif name == "LookupTableDecoder":
        from .pag_qec_framework import LookupTableDecoder

        return LookupTableDecoder
    elif name == "SurfaceCodeGeometry":
        from .surface_code_extension import SurfaceCodeGeometry

        return SurfaceCodeGeometry
    elif name == "SurfaceCodeEnvironment":
        from .surface_code_extension import SurfaceCodeEnvironment

        return SurfaceCodeEnvironment
    elif name == "SurfaceCodeNeuralDecoder":
        from .surface_code_extension import SurfaceCodeNeuralDecoder

        return SurfaceCodeNeuralDecoder
    elif name == "MWPMDecoder":
        from .surface_code_extension import MWPMDecoder

        return MWPMDecoder
    elif name == "CurriculumTrainer":
        from .surface_code_extension import CurriculumTrainer

        return CurriculumTrainer
    elif name == "ThreeQubitVisualizer":
        from .visualization import ThreeQubitVisualizer

        return ThreeQubitVisualizer
    elif name == "SurfaceCodeVisualizer":
        from .visualization import SurfaceCodeVisualizer

        return SurfaceCodeVisualizer
    elif name == "PerformanceVisualizer":
        from .visualization import PerformanceVisualizer

        return PerformanceVisualizer
    else:
        raise AttributeError(f"module 'quantum_research' has no attribute '{name}'")


__all__ = [
    # Core PAG-QEC
    "NeuralDecoder",
    "DecoderEnsemble",
    "ThreeQubitCodeEnvironment",
    "DecoderTrainer",
    "SpeculativeExecutionEngine",
    "LookupTableDecoder",
    # Surface Code Extension
    "SurfaceCodeGeometry",
    "SurfaceCodeEnvironment",
    "SurfaceCodeNeuralDecoder",
    "MWPMDecoder",
    "CurriculumTrainer",
    # Visualization
    "ThreeQubitVisualizer",
    "SurfaceCodeVisualizer",
    "PerformanceVisualizer",
]
