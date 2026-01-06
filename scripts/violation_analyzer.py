#!/usr/bin/env python3
"""
Violation Analysis and Prioritization Script

Analyzes complexity violations and prioritizes fixes based on impact scoring.
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass
class ViolationScore:
    """Scoring for a single violation."""

    file_path: str
    violation_type: str
    impact_score: int
    severity: str
    quick_fix: bool


def calculate_impact_score(metrics: Dict[str, Any], violation: str) -> ViolationScore:
    """Calculate impact score for a violation."""

    file_path = metrics["file_path"]
    base_score = 0
    severity = "medium"
    quick_fix = False

    # Scoring based on violation type
    if "File too large" in violation:
        base_score = 50
        severity = "high"
        if metrics["lines_of_code"] > 2000:
            base_score += 30
    elif "High cyclomatic complexity" in violation:
        base_score = 40
        severity = "high"
        if metrics["cyclomatic_complexity"] > 25:
            base_score += 20
    elif "Function too long" in violation:
        base_score = 20
        severity = "medium"
        quick_fix = True
        if metrics["max_function_length"] > 100:
            base_score += 15
    elif "Class too long" in violation:
        base_score = 35
        severity = "high"
        if metrics["max_class_length"] > 500:
            base_score += 25
    elif "Test file too large" in violation:
        base_score = 45
        severity = "high"
        quick_fix = True
    elif "Too many imports" in violation:
        base_score = 15
        severity = "low"
        quick_fix = True
    elif "Too many functions per class" in violation:
        base_score = 25
        severity = "medium"

    # File type multipliers
    if "test" in file_path.lower():
        base_score *= 1.3  # Tests are more critical
    if "core" in file_path:
        base_score *= 1.2  # Core components more important

    return ViolationScore(
        file_path=file_path,
        violation_type=violation,
        impact_score=int(base_score),
        severity=severity,
        quick_fix=quick_fix,
    )


def analyze_violations(json_path: str) -> Dict[str, Any]:
    """Analyze and prioritize all violations."""

    with open(json_path, "r") as f:
        data = json.load(f)

    all_scores = []
    violation_counts = {"high": 0, "medium": 0, "low": 0}

    for metrics in data["violations"]:
        for violation in metrics["violations"]:
            score = calculate_impact_score(metrics, violation)
            all_scores.append(score)
            violation_counts[score.severity] += 1

    # Sort by impact score (descending)
    all_scores.sort(key=lambda x: x.impact_score, reverse=True)

    # Calculate top 50% threshold
    top_50_count = len(all_scores) // 2
    top_violations = all_scores[:top_50_count]

    # Categorize by fix type
    quick_fixes = [s for s in top_violations if s.quick_fix]
    structural_fixes = [s for s in top_violations if not s.quick_fix]

    return {
        "summary": {
            "total_violations": len(all_scores),
            "top_50_count": top_50_count,
            "high_severity": violation_counts["high"],
            "medium_severity": violation_counts["medium"],
            "low_severity": violation_counts["low"],
            "quick_fixes": len(quick_fixes),
            "structural_fixes": len(structural_fixes),
        },
        "top_violations": [vars(s) for s in top_violations],
        "quick_fixes": [vars(s) for s in quick_fixes],
        "structural_fixes": [vars(s) for s in structural_fixes],
    }


def generate_prioritization_report(analysis: Dict[str, Any]) -> str:
    """Generate a human-readable prioritization report."""

    summary = analysis["summary"]
    top_violations = analysis["top_violations"]

    report = []
    report.append("=" * 80)
    report.append("COMPLEXITY VIOLATION PRIORITIZATION REPORT")
    report.append("=" * 80)
    report.append("")

    report.append("📊 SUMMARY:")
    report.append(f"Total violations: {summary['total_violations']}")
    report.append(f"Top 50% to fix: {summary['top_50_count']}")
    report.append(f"High severity: {summary['high_severity']}")
    report.append(f"Medium severity: {summary['medium_severity']}")
    report.append(f"Low severity: {summary['low_severity']}")
    report.append(f"Quick fixes: {summary['quick_fixes']}")
    report.append(f"Structural fixes: {summary['structural_fixes']}")
    report.append("")

    report.append("🎯 TOP PRIORITY VIOLATIONS (Top 50%):")
    report.append("-" * 50)

    for i, violation in enumerate(top_violations[:50], 1):  # Show first 50
        quick_indicator = "⚡" if violation["quick_fix"] else "🔧"
        severity_indicator = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
            violation["severity"], "⚪"
        )

        report.append(
            f"{i:2d}. {quick_indicator}{severity_indicator} [{violation['impact_score']:3d}] {violation['violation_type']}"
        )
        report.append(f"    📁 {violation['file_path']}")
        report.append("")

    if len(top_violations) > 50:
        report.append(f"... and {len(top_violations) - 50} more violations")
        report.append("")

    # Quick fixes section
    quick_fixes = analysis["quick_fixes"]
    if quick_fixes:
        report.append("⚡ QUICK FIXES (High Impact, Low Effort):")
        report.append("-" * 40)

        for i, fix in enumerate(quick_fixes[:20], 1):
            report.append(f"{i:2d}. [{fix['impact_score']:3d}] {fix['violation_type']}")
            report.append(f"    📁 {fix['file_path']}")
        report.append("")

    # Structural fixes section
    structural_fixes = analysis["structural_fixes"]
    if structural_fixes:
        report.append("🔧 STRUCTURAL FIXES (High Impact, Higher Effort):")
        report.append("-" * 45)

        for i, fix in enumerate(structural_fixes[:20], 1):
            report.append(f"{i:2d}. [{fix['impact_score']:3d}] {fix['violation_type']}")
            report.append(f"    📁 {fix['file_path']}")
        report.append("")

    report.append("📋 ACTION PLAN:")
    report.append("-" * 15)
    report.append("1. Start with quick fixes (low-hanging fruit)")
    report.append("2. Focus on test files first (highest impact)")
    report.append("3. Address file size violations through modularization")
    report.append("4. Break down complex functions into smaller units")
    report.append("5. Validate fixes with complexity monitor")
    report.append("")

    return "\n".join(report)


def main():
    """Main entry point."""

    if len(sys.argv) != 2:
        print("Usage: python violation_analyzer.py <violations_json_file>")
        sys.exit(1)

    json_path = sys.argv[1]
    if not Path(json_path).exists():
        print(f"Error: File {json_path} not found")
        sys.exit(1)

    # Analyze violations
    analysis = analyze_violations(json_path)

    # Generate report
    report = generate_prioritization_report(analysis)

    # Print report
    print(report)

    # Save detailed analysis
    output_path = "violation_prioritization.json"
    with open(output_path, "w") as f:
        json.dump(analysis, f, indent=2)

    print(f"📄 Detailed analysis saved to: {output_path}")


if __name__ == "__main__":
    main()
