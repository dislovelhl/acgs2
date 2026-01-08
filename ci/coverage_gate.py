import os
import sys
import xml.etree.ElementTree as ET


def check_coverage(file_path, threshold):
    if not os.path.exists(file_path):
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
            sys.exit(1)

        if rate >= threshold:
            sys.exit(0)
        else:
            sys.exit(1)

    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)

    gate_threshold = float(sys.argv[1])
    report_file = sys.argv[2] if len(sys.argv) > 2 else "coverage.xml"

    check_coverage(report_file, gate_threshold)
