#!/usr/bin/env python3
import subprocess
import sys


def classify_failure(command):
    print(f"Executing: {' '.join(command)}")
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    ret_code = process.returncode
    if ret_code == 0:
        print(stdout.decode())
        return 0

    err_msg = stderr.decode()
    print(err_msg, file=sys.stderr)

    classification = "logic-error"
    if "Connection" in err_msg or "Timeout" in err_msg:
        classification = "infrastructure-flake"
    elif "Policy" in err_msg or "forbidden" in err_msg.lower():
        classification = "policy-violation"
    elif "ModuleNotFoundError" in err_msg or "pip" in err_msg:
        classification = "external-dependency"

    print(f"\n❌ FAILURE CLASSIFIED: {classification}")

    # In CI, we could emit this as a GitHub Action notice
    # print(f"::error ::{classification} - Command failed with code {ret_code}")

    return ret_code


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: fail_wrap.py <command>")
        sys.exit(1)
    sys.exit(classify_failure(sys.argv[1:]))
