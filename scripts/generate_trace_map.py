#!/usr/bin/env python3
import json
import os
import re


def generate_trace_map(root_dir):
    trace_map = []
    # Pattern to find policy references in code: # policy: <id>
    # Or in docstrings: @policy <id>
    pattern = re.compile(r"(?:#|@)policy(?::|\s+)([A-Z0-9_\-]+)", re.IGNORECASE)

    for root, _, files in os.walk(root_dir):
        if ".git" in root or "venv" in root:
            continue
        for file in files:
            if not file.endswith((".py", ".rego", ".sh", ".yml")):
                continue

            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for i, line in enumerate(f, 1):
                        matches = pattern.findall(line)
                        for match in matches:
                            trace_map.append(
                                {
                                    "policy_id": match.upper(),
                                    "file": os.path.relpath(path, root_dir),
                                    "line": i,
                                    "context": line.strip(),
                                }
                            )
            except Exception:
                continue

    return trace_map


if __name__ == "__main__":
    results = generate_trace_map(".")
    print("### 🗺️ Policy Traceability Map")
    print("| Policy ID | File | Line | Context |")
    print("|-----------|------|------|---------|")
    for item in results:
        print(f"| {item['policy_id']} | {item['file']} | {item['line']} | `{item['context']}` |")

    with open("docs/POLICY_TRACE_MAP.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\n✅ Trace map saved to docs/POLICY_TRACE_MAP.json")
