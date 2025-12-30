import os
import sys
import xml.etree.ElementTree as ET


def check_coverage(file_path, threshold):
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        sys.exit(1)

    try:
        tree = ET.parse(file_path)
        root = tree.getroot()

        # In JaCoCo format or similar XML coverage reports, line-rate is usually in decimals
        if "line-rate" in root.attrib:
            rate = float(root.attrib["line-rate"]) * 100
        elif "lines-covered" in root.attrib and "lines-valid" in root.attrib:
            covered = int(root.attrib["lines-covered"])
            total = int(root.attrib["lines-valid"])
            rate = (covered / total) * 100 if total > 0 else 0
        else:
            # Fallback for other formats if necessary
            print(
                "Warning: Could not find 'line-rate' in XML root attributes. Check report format."
            )
            sys.exit(1)

        print(f"Current Line Coverage: {rate:.2f}% (Threshold: {threshold}%)")

        if rate >= threshold:
            print("Coverage gate PASSED.")
            sys.exit(0)
        else:
            print(f"Coverage gate FAILED: {rate:.2f}% < {threshold}%")
            sys.exit(1)

    except Exception as e:
        print(f"Error parsing coverage report: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python coverage_gate.py <threshold> [report_path]")
        sys.exit(1)

    gate_threshold = float(sys.argv[1])
    report_file = sys.argv[2] if len(sys.argv) > 2 else "coverage.xml"

    check_coverage(report_file, gate_threshold)
