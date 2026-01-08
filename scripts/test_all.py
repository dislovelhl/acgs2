#!/usr/bin/env python3
import os
import subprocess
import sys


def main():
    root = os.getcwd()

    # Detect virtual environment
    venv_python = os.path.join(root, ".venv", "bin", "python")
    if os.path.exists(venv_python):
        print(f"Using virtual environment: {venv_python}")
        python_exe = venv_python
    else:
        python_exe = sys.executable

    def run_test(name, path, env=None):
        print(f"=== Running {name} Tests ===")
        cmd = [python_exe, "-m", "pytest", path, "-v", "--tb=short"]
        try:
            current_env = os.environ.copy()
            if env:
                current_env.update(env)
            subprocess.check_call(cmd, env=current_env)
            print(f"--- {name} Tests PASSED ---\n")
            return True
        except subprocess.CalledProcessError:
            print(f"--- {name} Tests FAILED ---\n")
            return False

    core_path = os.path.join(root, "src/core")
    core_path = os.path.join(root, "src/core")

    # 1. Agent Workflows
    wf_passed = run_test(
        "Agent Workflows", ".agent/workflows/tests/", {"PYTHONPATH": f".:{core_path}"}
    )

    # 2. Performance
    perf_path = os.path.join(core_path, "testing/performance_test.py")
    print("=== Running Performance Tests ===")
    perf_passed = subprocess.call([python_exe, perf_path], env={"PYTHONPATH": core_path}) == 0
    print(f"--- Performance Tests {'PASSED' if perf_passed else 'FAILED'} ---\n")

    # 3. Enhanced Agent Bus
    bus_passed = run_test(
        "Enhanced Agent Bus",
        os.path.join(core_path, "enhanced_agent_bus/tests/"),
        {"PYTHONPATH": core_path},
    )

    # 4. Service Tests (Isolated root for each to avoid shadowing)
    services = [
        ("Policy Registry", "services/policy_registry"),
        ("Metering", "services/metering"),
        ("Constitutional Retrieval", "services/core/constitutional-retrieval-system"),
        ("Constraint Generation", "services/core/constraint_generation_system"),
        ("Audit Service", "services/audit_service"),
    ]

    service_results = {}
    for name, s_path in services:
        full_path = os.path.join(core_path, s_path)
        if os.path.exists(full_path):
            print(f"\n--- Running {name} Tests ---")
            # Isolate the service root in PYTHONPATH
            # Some tests are in the root of the service, others in /tests
            test_target = full_path
            if os.path.exists(os.path.join(full_path, "tests")):
                test_target = os.path.join(full_path, "tests")

            env = os.environ.copy()
            env["PYTHONPATH"] = f"{full_path}:{core_path}:{os.getcwd()}"
            service_results[name] = run_test(name, test_target, env)
        else:
            print(f"Skipping {name}: {full_path} not found")

    # 5. Observability Tests
    obs_path = os.path.join(root, "acgs2-observability")
    if os.path.exists(obs_path):
        obs_passed = run_test(
            "Observability",
            os.path.join(obs_path, "tests"),
            {"PYTHONPATH": f"{core_path}:{obs_path}"},
        )
    else:
        obs_passed = True  # Skip if not found

    # 6. Governance Experiments (Research)
    res_path = os.path.join(root, "acgs2-research/governance-experiments")
    if os.path.exists(res_path):
        gov_exp_passed = run_test(
            "Governance Experiments",
            os.path.join(res_path, "tests"),
            {"PYTHONPATH": f"{res_path}:{os.path.join(res_path, 'src')}"},
        )
    else:
        gov_exp_passed = True  # Skip if not found

    # Summary
    print("================ Summary ================")
    print(f"Agent Workflows: {'SUCCESS' if wf_passed else 'FAILED'}")
    print(f"Performance:     {'SUCCESS' if perf_passed else 'FAILED'}")
    print(f"Agent Bus:       {'SUCCESS' if bus_passed else 'FAILED'}")
    for name, passed in service_results.items():
        print(f"{name:16}: {'SUCCESS' if passed else 'FAILED'}")
    print(f"Observability:   {'SUCCESS' if obs_passed else 'FAILED'}")
    print(f"Gov Experiments: {'SUCCESS' if gov_exp_passed else 'FAILED'}")

    all_passed = all(
        [wf_passed, perf_passed, bus_passed, obs_passed, gov_exp_passed, *service_results.values()]
    )

    if all_passed:
        print("\nALL CRITICAL TEST SUITES PASSED")
        sys.exit(0)
    else:
        print("\nSOME TEST SUITES FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
