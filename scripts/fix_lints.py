import json
import re
from pathlib import Path


def fix_b904():
    with open("all_errors.json", "r") as f:
        errors = json.load(f)

    b904_errors = [e for e in errors if e["code"] == "B904"]
    files_to_fix = {}
    for e in b904_errors:
        path = e["filename"]
        if path not in files_to_fix:
            files_to_fix[path] = []
        files_to_fix[path].append(e)

    for path, errs in files_to_fix.items():
        file_path = Path(path)
        if not file_path.exists():
            continue

        content = file_path.read_text()
        lines = content.splitlines()

        # Sort errors by line number in reverse to avoid offset issues
        errs.sort(key=lambda x: x["location"]["row"], reverse=True)

        for e in errs:
            row = e["location"]["row"] - 1
            line = lines[row]
            if "raise " in line and " from " not in line:
                # Find the exception variable name from preceding lines if possible
                # Usually it's in the 'except Exception as e:' line
                exc_name = "e"  # default
                # Search backwards for 'except ... as ...:'
                for i in range(row - 1, max(-1, row - 10), -1):
                    match = re.search(r"except\s+.*?\s+as\s+(\w+)\s*:", lines[i])
                    if match:
                        exc_name = match.group(1)
                        break

                # Replace 'raise ...' with 'raise ... from exc_name'
                # But only if it ends the statement or is simple
                if line.strip().endswith(")"):
                    lines[row] = line + f" from {exc_name}"
                else:
                    # More complex case, just append ' from e' if it's a simple raise
                    if re.match(r"^\s*raise\s+\w+\(.*\)\s*$", line):
                        lines[row] = line + f" from {exc_name}"

        new_content = "\n".join(lines) + ("\n" if content.endswith("\n") else "")
        file_path.write_text(new_content)
        print(f"Fixed B904 in {path}")


if __name__ == "__main__":
    fix_b904()
