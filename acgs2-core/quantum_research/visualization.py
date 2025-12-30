#!/usr/bin/env python3
"""
Visualization Utilities for PAG-QEC Framework
Constitutional Hash: cdd01ef066bc6cf2

Provides ASCII and text-based visualizations for:
- 3-qubit bit-flip code states
- Surface code lattice layouts
- Syndrome patterns and corrections
- Decoder performance comparisons
- Training curves

No matplotlib dependency - uses pure ASCII art for terminal display.
"""

from typing import Dict, List, Optional, Set, Tuple

import numpy as np

# Constitutional hash for ACGS-2 compliance
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


# =============================================================================
# 3-QUBIT CODE VISUALIZATION
# =============================================================================


class ThreeQubitVisualizer:
    """
    ASCII visualization for the 3-qubit bit-flip code.

    Layout:
        [Q0]---[S1]---[Q1]---[S2]---[Q2]

    Where Qi are data qubits and Si are syndrome measurement locations.
    """

    @staticmethod
    def show_state(
        qubit_values: Tuple[int, int, int],
        syndrome: Tuple[int, int],
        error_qubit: int = -1,
        correction_qubit: int = -1,
    ) -> str:
        """
        Visualize the 3-qubit code state.

        Args:
            qubit_values: Tuple of (q0, q1, q2) values (0 or 1)
            syndrome: Tuple of (s1, s2) syndrome measurements
            error_qubit: Index of qubit with error (-1 if none)
            correction_qubit: Index of correction applied (-1 if none)

        Returns:
            ASCII string representation
        """
        q0, q1, q2 = qubit_values
        s1, s2 = syndrome

        # Qubit display with error/correction markers
        def qubit_str(i, val):
            marker = ""
            if i == error_qubit:
                marker = "X"  # Error marker
            if i == correction_qubit:
                marker = "C" if i != error_qubit else "XC"
            return f"[Q{i}:{val}{marker}]"

        # Build the visualization
        lines = [
            "┌─────────────────────────────────────────────────┐",
            "│         3-Qubit Bit-Flip Code State             │",
            "├─────────────────────────────────────────────────┤",
            "│                                                 │",
        ]

        # Qubit line
        q0s, q1s, q2s = qubit_str(0, q0), qubit_str(1, q1), qubit_str(2, q2)
        q_line = f"│   {q0s}───[S1:{s1}]───{q1s}───[S2:{s2}]───{q2s}   │"
        lines.append(q_line)

        lines.extend(
            [
                "│                                                 │",
                "├─────────────────────────────────────────────────┤",
                f"│ Syndrome: ({s1}, {s2})                              │",
            ]
        )

        # Interpretation
        syndrome_meaning = {
            (0, 0): "No error detected",
            (1, 0): "Error on Qubit 0",
            (1, 1): "Error on Qubit 1",
            (0, 1): "Error on Qubit 2",
        }
        meaning = syndrome_meaning.get(syndrome, "Unknown")
        lines.append(f"│ Meaning: {meaning:<38} │")

        if correction_qubit >= 0:
            lines.append(f"│ Correction: X on Qubit {correction_qubit}                       │")

        lines.append("└─────────────────────────────────────────────────┘")

        return "\n".join(lines)

    @staticmethod
    def show_encoding(logical_bit: int) -> str:
        """
        Show encoding of a logical bit.

        Args:
            logical_bit: 0 or 1

        Returns:
            ASCII representation of encoding
        """
        physical = (logical_bit, logical_bit, logical_bit)

        lines = [
            "┌───────────────────────────────────────┐",
            f"│ Encoding Logical |{logical_bit}⟩                  │",
            "├───────────────────────────────────────┤",
            f"│ |{logical_bit}⟩_L  →  |{physical[0]}{physical[1]}{physical[2]}⟩               │",
            "│                                       │",
            f"│ [Q0:{physical[0]}]───[Q1:{physical[1]}]───[Q2:{physical[2]}]           │",
            "│                                       │",
            "│ All three physical qubits store the   │",
            f"│ same value ({logical_bit}) for redundancy.      │",
            "└───────────────────────────────────────┘",
        ]

        return "\n".join(lines)

    @staticmethod
    def show_error_correction_cycle(
        initial: Tuple[int, int, int], error_qubit: int, syndrome: Tuple[int, int], correction: int
    ) -> str:
        """
        Visualize a complete error correction cycle.
        """
        q0, q1, q2 = initial
        errored = list(initial)
        if error_qubit >= 0:
            errored[error_qubit] ^= 1
        corrected = errored.copy()
        if correction >= 0:
            corrected[correction] ^= 1

        lines = [
            "╔═══════════════════════════════════════════════════════╗",
            "║            Error Correction Cycle                     ║",
            "╠═══════════════════════════════════════════════════════╣",
            "║ Step 1: Initial State                                 ║",
            f"║         |{q0}{q1}{q2}⟩ (Logical |{q0}⟩)                         ║",
            "║                                                       ║",
        ]

        if error_qubit >= 0:
            err_state = f"|{errored[0]}{errored[1]}{errored[2]}⟩"
            lines.extend(
                [
                    f"║ Step 2: Error Occurs (X on Q{error_qubit})                      ║",
                    f"║         {err_state:<44}║",
                    "║                                                       ║",
                ]
            )

        lines.extend(
            [
                f"║ Step 3: Measure Syndrome: ({syndrome[0]}, {syndrome[1]})                   ║",
            ]
        )

        syndrome_table = {
            (0, 0): "No error",
            (1, 0): "Error on Q0",
            (1, 1): "Error on Q1",
            (0, 1): "Error on Q2",
        }
        lines.append(f"║         → {syndrome_table.get(syndrome, 'Unknown'):<45}║")

        if correction >= 0:
            corr_state = f"|{corrected[0]}{corrected[1]}{corrected[2]}⟩ ✓"
            lines.extend(
                [
                    "║                                                       ║",
                    f"║ Step 4: Apply Correction (X on Q{correction})                   ║",
                    f"║         {corr_state:<44}║",
                ]
            )

        success = tuple(corrected) == initial
        result_msg = "SUCCESS - State Restored" if success else "FAILURE - Logical Error"
        lines.extend(
            [
                "║                                                       ║",
                f"║ Result: {result_msg:<45}║",
                "╚═══════════════════════════════════════════════════════╝",
            ]
        )

        return "\n".join(lines)


# =============================================================================
# SURFACE CODE VISUALIZATION
# =============================================================================


class SurfaceCodeVisualizer:
    """
    ASCII visualization for rotated surface codes.
    """

    @staticmethod
    def show_lattice(
        distance: int,
        x_errors: Optional[Set[int]] = None,
        z_errors: Optional[Set[int]] = None,
        x_syndrome: Optional[np.ndarray] = None,
        z_syndrome: Optional[np.ndarray] = None,
    ) -> str:
        """
        Visualize surface code lattice with errors and syndromes.

        Args:
            distance: Code distance (3, 5, 7, ...)
            x_errors: Set of qubit indices with X errors
            z_errors: Set of qubit indices with Z errors
            x_syndrome: X stabilizer measurement results
            z_syndrome: Z stabilizer measurement results

        Returns:
            ASCII representation
        """
        x_errors = x_errors or set()
        z_errors = z_errors or set()

        lines = [
            f"┌{'─' * (distance * 8 + 4)}┐",
            f"│ Distance-{distance} Rotated Surface Code {' ' * (distance * 8 - 26)}│",
            f"├{'─' * (distance * 8 + 4)}┤",
        ]

        # Build grid
        for row in range(distance):
            row_str = "│ "
            for col in range(distance):
                qubit_idx = row * distance + col

                # Determine qubit state marker
                if qubit_idx in x_errors and qubit_idx in z_errors:
                    marker = "Y"  # Both X and Z error
                elif qubit_idx in x_errors:
                    marker = "X"
                elif qubit_idx in z_errors:
                    marker = "Z"
                else:
                    marker = "·"

                row_str += f"[{marker}]"

                # Add horizontal connector
                if col < distance - 1:
                    row_str += "───"

            row_str += " │"
            lines.append(row_str)

            # Add vertical connectors (except last row)
            if row < distance - 1:
                vert_str = "│ "
                for col in range(distance):
                    vert_str += " │ "
                    if col < distance - 1:
                        # Stabilizer position
                        stab_idx = row * (distance - 1) + col

                        # Check if this stabilizer is triggered
                        is_x_defect = False
                        is_z_defect = False

                        if x_syndrome is not None and stab_idx < len(x_syndrome):
                            is_x_defect = x_syndrome[stab_idx] == 1
                        if z_syndrome is not None and stab_idx < len(z_syndrome):
                            is_z_defect = z_syndrome[stab_idx] == 1

                        if is_x_defect and is_z_defect:
                            vert_str += "[*]"
                        elif is_x_defect:
                            vert_str += "[X]"
                        elif is_z_defect:
                            vert_str += "[Z]"
                        else:
                            vert_str += " + "

                vert_str += " │"
                lines.append(vert_str)

        lines.append(f"├{'─' * (distance * 8 + 4)}┤")

        # Legend
        lines.extend(
            [
                "│ Legend:                              │",
                "│  [·] = No error                      │",
                "│  [X] = X error (bit-flip)            │",
                "│  [Z] = Z error (phase-flip)          │",
                "│  [Y] = Y error (both)                │",
                "│  [*] = Defect (syndrome = 1)         │",
                f"└{'─' * (distance * 8 + 4)}┘",
            ]
        )

        return "\n".join(lines)

    @staticmethod
    def show_syndrome_pattern(distance: int, x_syndrome: np.ndarray, z_syndrome: np.ndarray) -> str:
        """
        Visualize syndrome pattern separately.
        """
        x_defects = [i for i in range(len(x_syndrome)) if x_syndrome[i] == 1]
        z_defects = [i for i in range(len(z_syndrome)) if z_syndrome[i] == 1]

        lines = [
            "┌─────────────────────────────────────┐",
            f"│ Syndrome Pattern (d={distance})              │",
            "├─────────────────────────────────────┤",
            f"│ X-stabilizer defects: {x_defects or 'None':<13}│",
            f"│ Z-stabilizer defects: {z_defects or 'None':<13}│",
            "├─────────────────────────────────────┤",
        ]

        if len(x_defects) == 0 and len(z_defects) == 0:
            lines.append("│ ✓ No errors detected                │")
        elif len(x_defects) % 2 == 0 and len(z_defects) % 2 == 0:
            lines.append("│ Correctable error pattern           │")
        else:
            lines.append("│ ⚠ Boundary error (odd defects)     │")

        lines.append("└─────────────────────────────────────┘")

        return "\n".join(lines)


# =============================================================================
# PERFORMANCE VISUALIZATION
# =============================================================================


class PerformanceVisualizer:
    """
    ASCII visualization for decoder performance metrics.
    """

    @staticmethod
    def show_comparison_table(results: Dict[str, Dict]) -> str:
        """
        Show comparison table of decoder performance.

        Args:
            results: Dict mapping decoder name to metrics dict
                     Each metrics dict should have 'accuracy', 'latency_ns'
        """
        lines = [
            "┌────────────────────────────────────────────────────────────┐",
            "│                  Decoder Comparison                        │",
            "├──────────────────┬───────────┬─────────────┬──────────────┤",
            "│ Decoder          │ Accuracy  │ Latency     │ Status       │",
            "├──────────────────┼───────────┼─────────────┼──────────────┤",
        ]

        for name, metrics in results.items():
            acc = metrics.get("accuracy", 0) * 100
            lat_ns = metrics.get("latency_ns", 0)
            lat_us = lat_ns / 1000

            # Status based on targets
            if acc >= 99 and lat_us < 1:
                status = "✓ Excellent"
            elif acc >= 95 and lat_us < 10:
                status = "✓ Good"
            elif acc >= 90:
                status = "○ Acceptable"
            else:
                status = "✗ Needs work"

            lines.append(f"│ {name:<16} │ {acc:>7.2f}% │ {lat_us:>8.2f} µs │ {status:<12} │")

        lines.extend(
            [
                "├──────────────────┴───────────┴─────────────┴──────────────┤",
                "│ Targets: Accuracy ≥95%, Latency <10µs                     │",
                "└────────────────────────────────────────────────────────────┘",
            ]
        )

        return "\n".join(lines)

    @staticmethod
    def show_latency_histogram(
        latencies: List[float], num_bins: int = 10, label: str = "Latency Distribution"
    ) -> str:
        """
        Show ASCII histogram of latency distribution.

        Args:
            latencies: List of latency values in nanoseconds
            num_bins: Number of histogram bins
            label: Label for the histogram
        """
        if not latencies:
            return "No data"

        arr = np.array(latencies)
        min_val, max_val = arr.min(), arr.max()

        if min_val == max_val:
            # All same value
            counts = [len(latencies)]
            edges = [min_val, max_val + 1]
        else:
            counts, edges = np.histogram(arr, bins=num_bins)

        max_count = max(counts)
        bar_width = 40

        lines = [
            f"┌{'─' * 60}┐",
            f"│ {label:<58}│",
            f"├{'─' * 60}┤",
        ]

        for i, count in enumerate(counts):
            bar_len = int(count / max_count * bar_width) if max_count > 0 else 0
            bar = "█" * bar_len + "░" * (bar_width - bar_len)

            low = edges[i] / 1000  # Convert to µs
            high = edges[i + 1] / 1000

            lines.append(f"│ {low:>6.1f}-{high:<6.1f}µs │{bar}│ {count:>4} │")

        # Statistics
        p50_us = np.percentile(arr, 50) / 1000
        p99_us = np.percentile(arr, 99) / 1000
        max_us = arr.max() / 1000
        lines.extend(
            [
                f"├{'─' * 60}┤",
                f"│ P50: {p50_us:>8.2f} µs{' ' * 36}│",
                f"│ P99: {p99_us:>8.2f} µs{' ' * 36}│",
                f"│ Max: {max_us:>8.2f} µs{' ' * 36}│",
                f"└{'─' * 60}┘",
            ]
        )

        return "\n".join(lines)

    @staticmethod
    def show_training_curve(losses: List[float], accuracies: List[float], width: int = 50) -> str:
        """
        Show ASCII training curve.
        """
        if not losses or not accuracies:
            return "No training data"

        # Normalize for plotting
        max_loss = max(losses)
        min_loss = min(losses)

        height = 10

        lines = [
            "┌" + "─" * (width + 4) + "┐",
            "│ Training Progress" + " " * (width - 14) + "│",
            "├" + "─" * (width + 4) + "┤",
        ]

        # Plot area
        for row in range(height):
            threshold = 1 - row / height
            line = "│ "

            for col in range(width):
                idx = int(col / width * len(losses))
                if idx >= len(losses):
                    idx = len(losses) - 1

                # Normalize loss to [0, 1]
                if max_loss != min_loss:
                    norm_loss = (losses[idx] - min_loss) / (max_loss - min_loss)
                else:
                    norm_loss = 0.5

                if norm_loss >= threshold:
                    line += "█"
                else:
                    line += " "

            line += " │"
            lines.append(line)

        # X-axis
        start_acc = accuracies[0] * 100
        end_acc = accuracies[-1] * 100
        pad1 = " " * (width - 10)
        pad2 = " " * (width - 20)
        pad3 = " " * (width - 18)
        lines.extend(
            [
                "├" + "─" * (width + 4) + "┤",
                f"│ Epoch: 0{pad1}→ {len(losses)} │",
                f"│ Loss:  {max_loss:.4f}{pad2}→ {losses[-1]:.4f} │",
                f"│ Acc:   {start_acc:.1f}%{pad3}→ {end_acc:.1f}% │",
                "└" + "─" * (width + 4) + "┘",
            ]
        )

        return "\n".join(lines)


# =============================================================================
# DEMO FUNCTIONS
# =============================================================================


def demo_three_qubit():
    """Demonstrate 3-qubit code visualization."""
    viz = ThreeQubitVisualizer()

    print("\n" + "=" * 60)
    print("THREE-QUBIT BIT-FLIP CODE VISUALIZATION")
    print("=" * 60)

    # Show encoding
    print("\n" + viz.show_encoding(0))
    print("\n" + viz.show_encoding(1))

    # Show error correction cycle
    print(
        "\n"
        + viz.show_error_correction_cycle(
            initial=(0, 0, 0), error_qubit=1, syndrome=(1, 1), correction=1
        )
    )

    # Show state with error
    print(
        "\n"
        + viz.show_state(qubit_values=(0, 1, 0), syndrome=(1, 1), error_qubit=1, correction_qubit=1)
    )


def demo_surface_code():
    """Demonstrate surface code visualization."""
    viz = SurfaceCodeVisualizer()

    print("\n" + "=" * 60)
    print("SURFACE CODE VISUALIZATION")
    print("=" * 60)

    # Distance-3 with errors
    print("\n" + viz.show_lattice(distance=3, x_errors={4}, z_errors={0, 8}))  # Center qubit

    # Syndrome pattern
    x_syn = np.array([1, 0, 0, 1])
    z_syn = np.array([0, 1, 0, 0])
    print("\n" + viz.show_syndrome_pattern(3, x_syn, z_syn))


def demo_performance():
    """Demonstrate performance visualization."""
    viz = PerformanceVisualizer()

    print("\n" + "=" * 60)
    print("PERFORMANCE VISUALIZATION")
    print("=" * 60)

    # Comparison table
    results = {
        "Lookup Table": {"accuracy": 1.0, "latency_ns": 500},
        "Neural (FP32)": {"accuracy": 0.97, "latency_ns": 8000},
        "Neural (INT8)": {"accuracy": 0.96, "latency_ns": 2000},
        "Speculative": {"accuracy": 0.97, "latency_ns": 1500},
    }
    print("\n" + viz.show_comparison_table(results))

    # Latency histogram
    latencies = np.random.exponential(2000, 1000).tolist()
    print("\n" + viz.show_latency_histogram(latencies, num_bins=8))

    # Training curve
    epochs = 100
    losses = [1.0 * np.exp(-i / 30) + 0.1 * np.random.random() for i in range(epochs)]
    accuracies = [
        0.5 + 0.45 * (1 - np.exp(-i / 20)) + 0.02 * np.random.random() for i in range(epochs)
    ]
    print("\n" + viz.show_training_curve(losses, accuracies))


def main():
    """Run all visualization demos."""
    print(
        """
    ╔═══════════════════════════════════════════════════════════════╗
    ║  PAG-QEC Visualization Utilities                              ║
    ║  Constitutional Hash: cdd01ef066bc6cf2                        ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    )

    demo_three_qubit()
    demo_surface_code()
    demo_performance()

    print("\n" + "=" * 60)
    print("VISUALIZATION UTILITIES READY")
    print("=" * 60)


if __name__ == "__main__":
    main()
